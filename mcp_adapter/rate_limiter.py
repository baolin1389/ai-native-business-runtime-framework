"""
Rate Limiter Implementation

Implements token bucket algorithm for provider-aware rate limiting.
"""

import asyncio
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from collections import deque


@dataclass
class RateLimitConfig:
    """Rate limit configuration for a provider"""
    requests_per_minute: int = 60
    tokens_per_minute: Optional[int] = None
    requests_per_day: Optional[int] = None
    tokens_per_day: Optional[int] = None


class TokenBucket:
    """
    Token bucket algorithm for rate limiting.

    Tokens are added to the bucket at a constant rate.
    Each request consumes tokens. If insufficient tokens,
    the request must wait.
    """

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.

        Args:
            capacity: Maximum tokens in bucket
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Acquire tokens from bucket.

        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum seconds to wait (None = wait forever)

        Returns:
            True if tokens acquired, False if timeout
        """
        async with self._lock:
            await self._refill()

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True

            # Calculate wait time for tokens to become available
            tokens_needed = tokens - self._tokens
            wait_time = tokens_needed / self.refill_rate

            if timeout is not None and wait_time > timeout:
                return False

            # Wait and refill
            await asyncio.sleep(wait_time)
            await self._refill()
            self._tokens -= tokens
            return True

    async def _refill(self) -> None:
        """Refill tokens based on elapsed time"""
        now = time.monotonic()
        elapsed = now - self._last_refill
        new_tokens = elapsed * self.refill_rate
        self._tokens = min(self.capacity, self._tokens + new_tokens)
        self._last_refill = now

    @property
    def available_tokens(self) -> float:
        """Get current available tokens (approximate)"""
        return self._tokens


class RateLimiter:
    """
    Rate limiter for AI provider requests.

    Manages multiple rate limit dimensions:
    - Requests per minute
    - Tokens per minute
    - Requests per day (optional)
    - Tokens per day (optional)
    """

    def __init__(self, config: RateLimitConfig):
        self.config = config

        # Initialize token buckets for each dimension
        self._rpm_bucket = TokenBucket(
            capacity=config.requests_per_minute,
            refill_rate=config.requests_per_minute / 60.0
        )

        if config.tokens_per_minute:
            self._tpm_bucket = TokenBucket(
                capacity=config.tokens_per_minute,
                refill_rate=config.tokens_per_minute / 60.0
            )
        else:
            self._tpm_bucket = None

        # Daily buckets
        if config.requests_per_day:
            self._rpd_bucket = TokenBucket(
                capacity=config.requests_per_day,
                refill_rate=config.requests_per_day / 86400.0
            )
        else:
            self._rpd_bucket = None

        if config.tokens_per_day:
            self._tpd_bucket = TokenBucket(
                capacity=config.tokens_per_day,
                refill_rate=config.tokens_per_day / 86400.0
            )
        else:
            self._tpd_bucket = None

        # Track recent requests for adaptive limiting
        self._request_times: deque = deque(maxlen=1000)

    async def acquire(
        self,
        tokens: int = 0,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Acquire rate limit clearance for a request.

        Args:
            tokens: Token count for the request (0 for no token tracking)
            timeout: Maximum seconds to wait

        Returns:
            True if clearance granted, False if timeout
        """
        # Check RPM
        if not await self._rpm_bucket.acquire(1, timeout):
            return False

        # Check TPM if tokens specified
        if tokens > 0 and self._tpm_bucket:
            if not await self._tpm_bucket.acquire(tokens, timeout):
                # Rollback RPM acquire
                return False

        # Check daily limits if configured
        if self._rpd_bucket:
            if not await self._rpd_bucket.acquire(1, timeout):
                return False

        if tokens > 0 and self._tpd_bucket:
            if not await self._tpd_bucket.acquire(tokens, timeout):
                return False

        self._request_times.append(time.monotonic())
        return True

    def get_wait_time(self, tokens: int = 0) -> float:
        """
        Get estimated wait time in seconds.

        Args:
            tokens: Token count for the request

        Returns:
            Estimated wait time
        """
        wait = 0.0

        # Calculate tokens needed from RPM bucket
        available = self._rpm_bucket.available_tokens
        if available < 1:
            wait = max(wait, (1 - available) / self._rpm_bucket.refill_rate)

        if tokens > 0 and self._tpm_bucket:
            available = self._tpm_bucket.available_tokens
            if available < tokens:
                wait = max(wait, (tokens - available) / self._tpm_bucket.refill_rate)

        return wait

    def get_stats(self) -> Dict[str, Any]:
        """Get current rate limiter statistics"""
        return {
            "rpm_available": self._rpm_bucket.available_tokens,
            "rpm_capacity": self.config.requests_per_minute,
            "tpm_available": self._tpm_bucket.available_tokens if self._tpm_bucket else None,
            "tpm_capacity": self.config.tokens_per_minute,
            "recent_requests": len(self._request_times),
            "requests_last_minute": self._count_recent_requests(60),
        }

    def _count_recent_requests(self, seconds: float) -> int:
        """Count requests in the last N seconds"""
        cutoff = time.monotonic() - seconds
        return sum(1 for t in self._request_times if t > cutoff)


class AdaptiveRateLimiter(RateLimiter):
    """
    Rate limiter that adapts based on 429 responses.

    When a rate limit is hit, reduces limits temporarily
    and gradually restores them.
    """

    def __init__(self, config: RateLimitConfig):
        super().__init__(config)
        self._reduction_factor = 1.0
        self._min_factor = 0.1
        self._recovery_time: Optional[float] = None
        self._backoff_until: Optional[float] = None

    async def on_rate_limit_hit(self, retry_after: Optional[int] = None) -> None:
        """
        Handle rate limit being exceeded.

        Reduces capacity temporarily.
        """
        self._reduction_factor = max(self._min_factor, self._reduction_factor * 0.5)
        self._backoff_until = time.monotonic() + (retry_after or 60)

    async def on_success(self) -> None:
        """
        Handle successful request.

        Gradually recovers reduced capacity.
        """
        if self._reduction_factor < 1.0:
            if time.monotonic() >= self._backoff_until:
                self._reduction_factor = min(1.0, self._reduction_factor * 1.1)

    def get_effective_limit(self, limit_type: str) -> int:
        """Get effective limit after adaptation"""
        base = getattr(self.config, f"{limit_type}_per_minute", 0) or \
               getattr(self.config, f"{limit_type}_per_day", 0) or 0
        return int(base * self._reduction_factor)

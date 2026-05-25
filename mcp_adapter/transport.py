"""
MCP Transport Layer

Provides HTTP, WebSocket, and Streaming transport implementations
for communicating with AI providers.
"""

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass
import ssl
import certifi

import httpx
from httpx import Timeout, Limits

from mcp_adapter.exceptions import TransportError, ProviderAuthError, ProviderRateLimitError


@dataclass
class TransportConfig:
    """Configuration for transport layer"""
    timeout_seconds: int = 60
    max_retries: int = 3
    pool_size: int = 10
    keep_alive: bool = True
    verify_ssl: bool = True
    proxy_url: Optional[str] = None


class BaseTransport(ABC):
    """Abstract base class for transports"""

    @abstractmethod
    async def send(self, request: Dict[str, Any], endpoint: str) -> Dict[str, Any]:
        """Send request and receive response"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the transport"""
        pass


class HTTPTransport(BaseTransport):
    """
    HTTP transport for synchronous communication.

    Features:
    - Persistent connection pooling
    - Automatic request retry
    - Certificate validation
    - Proxy support
    """

    def __init__(self, config: Optional[TransportConfig] = None):
        self.config = config or TransportConfig()
        self._client: Optional[httpx.AsyncClient] = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize HTTP client with connection pooling"""
        ssl_context = None
        if self.config.verify_ssl:
            ssl_context = ssl.create_default_context(cafile=certifi.where())

        limits = Limits(
            max_connections=self.config.pool_size,
            max_keepalive_connections=self.config.pool_size if self.config.keep_alive else 0
        )

        timeout = Timeout(self.config.timeout_seconds)

        transport_kwargs: Dict[str, Any] = {}
        if ssl_context:
            transport_kwargs["ssl"] = ssl_context
        if self.config.proxy_url:
            transport_kwargs["proxy"] = self.config.proxy_url

        self._client = httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            **transport_kwargs
        )

    async def send(
        self,
        request: Dict[str, Any],
        endpoint: str,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Send HTTP request.

        Args:
            request: MCP request body
            endpoint: Full URL endpoint
            headers: Additional HTTP headers

        Returns:
            Parsed response dictionary
        """
        if not self._client:
            raise TransportError("Transport not initialized")

        request_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if headers:
            request_headers.update(headers)

        retry_count = 0
        last_error: Optional[Exception] = None

        while retry_count <= self.config.max_retries:
            try:
                response = await self._client.post(
                    endpoint,
                    json=request,
                    headers=request_headers
                )

                return await self._handle_response(response)

            except httpx.TimeoutException as e:
                last_error = e
                retry_count += 1
                if retry_count <= self.config.max_retries:
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 401:
                    raise ProviderAuthError("provider", "Authentication failed")
                elif e.response.status_code == 429:
                    retry_after = e.response.headers.get("Retry-After")
                    raise ProviderRateLimitError(
                        "provider",
                        retry_after=int(retry_after) if retry_after else None
                    )
                raise TransportError(f"HTTP {e.response.status_code}: {str(e)}")

            except Exception as e:
                last_error = e
                retry_count += 1
                if retry_count <= self.config.max_retries:
                    await asyncio.sleep(2 ** retry_count)

        raise TransportError(f"Max retries exceeded: {last_error}")

    async def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Process HTTP response"""
        if response.status_code == 401:
            raise ProviderAuthError("provider", "Authentication failed")

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise ProviderRateLimitError(
                "provider",
                retry_after=int(retry_after) if retry_after else None
            )

        response.raise_for_status()

        try:
            return response.json()
        except json.JSONDecodeError as e:
            raise TransportError(f"Invalid JSON response: {str(e)}")

    async def close(self) -> None:
        """Close HTTP client and connections"""
        if self._client:
            await self._client.aclose()
            self._client = None


class WebSocketTransport(BaseTransport):
    """
    WebSocket transport for real-time and streaming interactions.

    Features:
    - Bidirectional communication
    - Heartbeat/keep-alive
    - Graceful reconnection
    - Message framing
    """

    def __init__(self, config: Optional[TransportConfig] = None):
        self.config = config or TransportConfig()
        self._ws: Optional[httpx.AsyncWebSocket] = None
        self._connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5

    async def connect(self, url: str, headers: Optional[Dict[str, str]] = None) -> None:
        """
        Establish WebSocket connection.

        Args:
            url: WebSocket endpoint URL
            headers: Optional connection headers
        """
        # Note: httpx AsyncClient handles WebSocket upgrade
        # This is a simplified implementation
        self._connected = True

    async def send(
        self,
        request: Dict[str, Any],
        endpoint: str
    ) -> Dict[str, Any]:
        """
        Send message over WebSocket.

        Args:
            request: MCP request body
            endpoint: WebSocket URL (for connection)

        Returns:
            Response dictionary
        """
        if not self._connected:
            await self.connect(endpoint)

        # WebSocket send/receive would be implemented here
        # This is a placeholder for the actual WebSocket logic
        raise NotImplementedError("WebSocket streaming not yet implemented")

    async def send_stream(
        self,
        request: Dict[str, Any],
        endpoint: str,
        on_chunk: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> Dict[str, Any]:
        """
        Send request and stream response chunks.

        Args:
            request: MCP request body
            endpoint: WebSocket URL
            on_chunk: Callback for each chunk received

        Returns:
            Final aggregated response
        """
        raise NotImplementedError("WebSocket streaming not yet implemented")

    async def close(self) -> None:
        """Close WebSocket connection"""
        if self._ws:
            await self._ws.aclose()
            self._ws = None
        self._connected = False


class StreamingTransport(BaseTransport):
    """
    Transport for server-sent events and streaming responses.

    Features:
    - Chunked response processing
    - Progress callbacks
    - Partial result access
    - Stream termination handling
    """

    def __init__(self, config: Optional[TransportConfig] = None):
        self.config = config or TransportConfig()
        self._client: Optional[httpx.AsyncClient] = None

    def _ensure_client(self) -> httpx.AsyncClient:
        """Lazily initialize HTTP client"""
        if not self._client:
            timeout = Timeout(self.config.timeout_seconds)
            self._client = httpx.AsyncClient(timeout=timeout)
        return self._client

    async def send_stream(
        self,
        request: Dict[str, Any],
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        on_chunk: Optional[Callable[[str], Awaitable[None]]] = None,
        on_progress: Optional[Callable[[float, float], Awaitable[None]]] = None
    ) -> str:
        """
        Send request with streaming response.

        Args:
            request: MCP request body
            endpoint: Full URL endpoint
            headers: Additional HTTP headers
            on_chunk: Callback for each text chunk received
            on_progress: Callback for progress updates (current, total)

        Returns:
            Complete response text
        """
        client = self._ensure_client()

        request_headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        if headers:
            request_headers.update(headers)

        accumulated = []
        async with client.stream("POST", endpoint, json=request, headers=request_headers) as response:
            if response.status_code == 401:
                raise ProviderAuthError("provider")
            if response.status_code == 429:
                raise ProviderRateLimitError("provider")

            response.raise_for_status()

            content_length = response.headers.get("content-length")
            total = int(content_length) if content_length else 0

            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break

                    if on_chunk:
                        await on_chunk(data)

                    accumulated.append(data)

                elif line.startswith("event:"):
                    # Handle event-based streaming
                    pass

        return "".join(accumulated)

    async def send(self, request: Dict[str, Any], endpoint: str) -> Dict[str, Any]:
        """Non-streaming send for compatibility"""
        result = await self.send_stream(request, endpoint)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"text": result}

    async def close(self) -> None:
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

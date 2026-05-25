"""
MCP Adapter Client

High-level client for interacting with AI providers through MCP.
"""

import asyncio
from typing import Dict, Any, Optional, List, AsyncIterator

from mcp_adapter.config import MCPAdapterConfig, load_config, ProviderConfig
from mcp_adapter.protocol import ProtocolHandler
from mcp_adapter.transport import HTTPTransport, WebSocketTransport, StreamingTransport, TransportConfig
from mcp_adapter.rate_limiter import RateLimiter, RateLimitConfig, AdaptiveRateLimiter
from mcp_adapter.providers import (
    BaseProvider, OpenAIProvider, AnthropicProvider,
    GoogleProvider, CustomProvider, ModelResponse
)
from mcp_adapter.providers.base import Message, ToolDefinition, ToolCall, MessageRole
from mcp_adapter.exceptions import MCPError


class MCPAdapterClient:
    """
    High-level MCP Adapter client.

    Provides a unified interface for interacting with multiple AI providers
    while handling transport, protocol, rate limiting, and error management.
    """

    def __init__(self, config: Optional[MCPAdapterConfig] = None):
        """
        Initialize MCP Adapter client.

        Args:
            config: MCP adapter configuration. Loads from environment if not provided.
        """
        self.config = config or load_config()
        self._providers: Dict[str, BaseProvider] = {}
        self._default_provider: Optional[str] = None

    async def initialize(self) -> None:
        """Initialize transport and provider connections."""
        for name, provider_config in self.config.providers.items():
            self._providers[name] = await self._create_provider(name, provider_config)

        self._default_provider = self.config.default_provider

    async def _create_provider(self, name: str, config: ProviderConfig) -> BaseProvider:
        """Create provider instance with appropriate transport."""
        # Create rate limiter for this provider
        rate_limit_config = RateLimitConfig(
            requests_per_minute=self.config.rate_limit.requests_per_minute,
            tokens_per_minute=self.config.rate_limit.tokens_per_minute,
            requests_per_day=self.config.rate_limit.requests_per_day,
            tokens_per_day=self.config.rate_limit.tokens_per_day,
        )
        rate_limiter = AdaptiveRateLimiter(rate_limit_config)

        # Create transport based on config
        transport_config = TransportConfig(
            timeout_seconds=self.config.timeout_seconds,
            max_retries=self.config.max_retries,
            pool_size=self.config.transport.pool_size,
            keep_alive=self.config.transport.keep_alive,
            verify_ssl=self.config.transport.verify_ssl,
            proxy_url=self.config.transport.proxy_url,
        )

        transport: BaseTransport
        if self.config.transport.type.value == "http":
            transport = HTTPTransport(transport_config)
        elif self.config.transport.type.value == "websocket":
            transport = WebSocketTransport(transport_config)
        else:
            transport = HTTPTransport(transport_config)

        # Create provider based on name
        provider: BaseProvider
        if name == "openai":
            provider = OpenAIProvider(config, transport, rate_limiter)
        elif name == "anthropic":
            provider = AnthropicProvider(config, transport, rate_limiter)
        elif name == "google":
            provider = GoogleProvider(config, transport, rate_limiter)
        else:
            provider = CustomProvider(config, transport, rate_limiter)

        return provider

    async def complete(
        self,
        messages: List[Message],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs
    ) -> ModelResponse:
        """
        Send completion request.

        Args:
            messages: List of chat messages
            provider: Provider name (uses default if not specified)
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            tools: Optional tool definitions

        Returns:
            ModelResponse from the provider
        """
        provider_name = provider or self._default_provider
        if not provider_name or provider_name not in self._providers:
            raise ValueError(f"Provider not found: {provider_name}")

        provider_instance = self._providers[provider_name]

        try:
            return await provider_instance.complete(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                **kwargs
            )
        except MCPError:
            raise
        except Exception as e:
            raise MCPError(
                code=-32603,
                message=f"Request failed: {str(e)}"
            )

    async def complete_stream(
        self,
        messages: List[Message],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream completion response.

        Args:
            messages: List of chat messages
            provider: Provider name
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            tools: Optional tool definitions

        Yields:
            Content chunks as they arrive
        """
        provider_name = provider or self._default_provider
        if not provider_name or provider_name not in self._providers:
            raise ValueError(f"Provider not found: {provider_name}")

        provider_instance = self._providers[provider_name]

        try:
            async for chunk in provider_instance.complete_stream(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                **kwargs
            ):
                yield chunk
        except MCPError:
            raise
        except Exception as e:
            raise MCPError(
                code=-32603,
                message=f"Stream failed: {str(e)}"
            )

    def get_provider(self, name: Optional[str] = None) -> BaseProvider:
        """Get provider instance by name."""
        provider_name = name or self._default_provider
        if provider_name not in self._providers:
            raise ValueError(f"Provider not found: {provider_name}")
        return self._providers[provider_name]

    def provider_supports(self, name: Optional[str] = None, capability: str = None) -> bool:
        """Check if provider supports a capability."""
        provider = self.get_provider(name)
        return capability in provider.capabilities

    async def close(self) -> None:
        """Close all provider connections."""
        for provider in self._providers.values():
            await provider.close()
        self._providers.clear()

    @property
    def providers(self) -> List[str]:
        """List of available provider names."""
        return list(self._providers.keys())


# Helper function for simple use cases
async def create_client(config_path: Optional[str] = None) -> MCPAdapterClient:
    """
    Create and initialize an MCP adapter client.

    Args:
        config_path: Optional path to configuration file

    Returns:
        Initialized MCPAdapterClient
    """
    client = MCPAdapterClient(load_config(config_path) if config_path else None)
    await client.initialize()
    return client

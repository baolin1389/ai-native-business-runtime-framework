"""
Anthropic Provider Adapter

Implements the Anthropic API integration for Claude completions,
tool use, vision support, and streaming.

Endpoint: https://api.anthropic.com/v1/*
"""

from typing import Dict, Any, Optional, List, AsyncIterator

from mcp_adapter.config import ProviderConfig
from mcp_adapter.transport import BaseTransport
from mcp_adapter.rate_limiter import RateLimiter as BaseRateLimiter
from mcp_adapter.providers.base import (
    BaseProvider, ModelResponse, Message, ToolDefinition, ToolCall
)
from mcp_adapter.exceptions import ProviderAuthError, ProviderRateLimitError


class AnthropicProvider(BaseProvider):
    """
    Anthropic API provider.

    Capabilities:
    - Claude completions
    - Tool use
    - Vision support
    - Streaming
    """

    def __init__(
        self,
        config: ProviderConfig,
        transport: BaseTransport,
        rate_limiter: BaseRateLimiter
    ):
        super().__init__(config, transport, rate_limiter)

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {
            "x-api-key": self.config.api_key_env,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        headers.update(self.config.extra_headers)
        return headers

    async def complete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs
    ) -> ModelResponse:
        """
        Send completion request to Anthropic Claude.

        Args:
            messages: List of conversation messages
            model: Model name (defaults to config default)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            tools: Tool definitions for tool use

        Returns:
            ModelResponse with completion
        """
        model = model or self.config.default_model

        # Acquire rate limit clearance
        estimated_tokens = sum(self._estimate_tokens(m.content) for m in messages)
        if not await self.rate_limiter.acquire(tokens=estimated_tokens):
            raise ProviderRateLimitError(self.name, retry_after=60)

        # Build request - Claude uses different format
        endpoint = f"{self.config.endpoint}/messages"
        
        # Claude requires max_tokens
        if max_tokens is None:
            max_tokens = 4096

        request_body: Dict[str, Any] = {
            "model": model,
            "messages": self._prepare_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            request_body["tools"] = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.parameters,
                }
                for tool in tools
            ]

        request_body.update(kwargs)

        # Send request
        response = await self.transport.send(
            request_body,
            endpoint,
            headers=self._get_headers()
        )

        return self._parse_response(response, model)

    async def complete_stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream completion from Anthropic Claude.

        Yields:
            Content delta strings as they arrive
        """
        model = model or self.config.default_model

        endpoint = f"{self.config.endpoint}/messages"
        
        if max_tokens is None:
            max_tokens = 4096

        request_body: Dict[str, Any] = {
            "model": model,
            "messages": self._prepare_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        if tools:
            request_body["tools"] = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.parameters,
                }
                for tool in tools
            ]

        request_body.update(kwargs)

        # Stream response
        response = await self.transport.send(
            request_body,
            endpoint,
            headers=self._get_headers()
        )

        # Parse streaming response
        if "content" in response:
            for block in response["content"]:
                if block.get("type") == "text":
                    yield block.get("text", "")

    def _prepare_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert messages to Anthropic format"""
        result = []
        for msg in messages:
            if msg.role.value == "system":
                # System messages handled separately in Claude
                continue
            result.append({
                "role": msg.role.value,
                "content": msg.content,
            })
        return result

    def _parse_response(self, response: Dict[str, Any], model: str) -> ModelResponse:
        """Parse Anthropic API response"""
        content = response.get("content", [])
        
        text_content = []
        tool_calls = []

        for block in content:
            if block.get("type") == "text":
                text_content.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.get("id", ""),
                    name=block.get("name", ""),
                    arguments=block.get("input", {})
                ))

        return ModelResponse(
            content="".join(text_content),
            model=model,
            finish_reason=response.get("stop_reason"),
            tool_calls=tool_calls,
            usage={
                "input_tokens": response.get("usage", {}).get("input_tokens", 0),
                "output_tokens": response.get("usage", {}).get("output_tokens", 0),
            },
            raw_response=response
        )

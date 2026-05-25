"""
Custom Provider Adapter

For self-hosted or custom model endpoints with configurable
authentication and protocol translation.
"""

from typing import Dict, Any, Optional, List, AsyncIterator

from mcp_adapter.config import ProviderConfig
from mcp_adapter.transport import BaseTransport
from mcp_adapter.rate_limiter import RateLimiter as BaseRateLimiter
from mcp_adapter.providers.base import (
    BaseProvider, ModelResponse, Message, ToolDefinition, ToolCall
)
from mcp_adapter.exceptions import ProviderAuthError, ProviderRateLimitError


class CustomProvider(BaseProvider):
    """
    Custom/self-hosted model provider.

    Features:
    - Configurable endpoint
    - Custom authentication
    - Protocol translation
    """

    def __init__(
        self,
        config: ProviderConfig,
        transport: BaseTransport,
        rate_limiter: BaseRateLimiter
    ):
        super().__init__(config, transport, rate_limiter)

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with custom auth"""
        headers = {
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
        Send completion request to custom endpoint.

        Args:
            messages: List of conversation messages
            model: Model identifier (may be ignored by custom provider)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            tools: Tool definitions (provider may not support)

        Returns:
            ModelResponse with completion
        """
        # Acquire rate limit clearance
        estimated_tokens = sum(self._estimate_tokens(m.content) for m in messages)
        if not await self.rate_limiter.acquire(tokens=estimated_tokens):
            raise ProviderRateLimitError(self.name, retry_after=60)

        # Build request
        endpoint = f"{self.config.endpoint}/chat/completions"
        request_body: Dict[str, Any] = {
            "model": model or "default",
            "messages": self._prepare_messages(messages),
            "temperature": temperature,
        }

        if max_tokens:
            request_body["max_tokens"] = max_tokens

        if tools:
            request_body["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    }
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

        return self._parse_response(response, model or "custom")

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
        Stream completion from custom endpoint.

        Yields:
            Content delta strings as they arrive
        """
        endpoint = f"{self.config.endpoint}/chat/completions"
        request_body: Dict[str, Any] = {
            "model": model or "default",
            "messages": self._prepare_messages(messages),
            "temperature": temperature,
            "stream": True,
        }

        if max_tokens:
            request_body["max_tokens"] = max_tokens

        if tools:
            request_body["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    }
                }
                for tool in tools
            ]

        request_body.update(kwargs)

        # Use streaming transport
        accumulated = ""
        async for chunk in self._stream_request(request_body, endpoint):
            accumulated += chunk
            yield chunk

    async def _stream_request(
        self,
        request_body: Dict[str, Any],
        endpoint: str
    ) -> AsyncIterator[str]:
        """Send streaming request and yield chunks"""
        response = await self.transport.send(
            request_body,
            endpoint,
            headers=self._get_headers()
        )

        if "choices" in response:
            delta = response["choices"][0].get("delta", {})
            content = delta.get("content", "")
            if content:
                yield content

    def _parse_response(self, response: Dict[str, Any], model: str) -> ModelResponse:
        """Parse custom provider response"""
        choices = response.get("choices", [])
        if not choices:
            raise Exception("No choices in response")

        choice = choices[0]
        message = choice.get("message", {})

        # Parse tool calls if present
        tool_calls = []
        raw_tool_calls = message.get("tool_calls", [])
        if raw_tool_calls:
            for tc in raw_tool_calls:
                func = tc.get("function", {})
                tool_calls.append(ToolCall(
                    id=tc.get("id", ""),
                    name=func.get("name", ""),
                    arguments=self._parse_json_arguments(func.get("arguments", "{}"))
                ))

        return ModelResponse(
            content=message.get("content", ""),
            model=model,
            finish_reason=choice.get("finish_reason"),
            tool_calls=tool_calls,
            usage=response.get("usage", {}),
            raw_response=response
        )

    def _parse_json_arguments(self, args_str: str) -> Dict[str, Any]:
        """Parse JSON string arguments"""
        import json
        try:
            return json.loads(args_str) if isinstance(args_str, str) else args_str
        except json.JSONDecodeError:
            return {}

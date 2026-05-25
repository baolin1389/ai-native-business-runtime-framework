"""
OpenAI Provider Adapter

Implements the OpenAI API integration for chat completions, embeddings,
function calling, and vision support.

Endpoint: https://api.openai.com/v1/*
"""

from typing import Dict, Any, Optional, List, AsyncIterator

from mcp_adapter.config import ProviderConfig
from mcp_adapter.transport import BaseTransport
from mcp_adapter.rate_limiter import RateLimiter as BaseRateLimiter
from mcp_adapter.providers.base import (
    BaseProvider, ModelResponse, Message, ToolDefinition, ToolCall
)
from mcp_adapter.exceptions import ProviderAuthError, ProviderRateLimitError


class OpenAIProvider(BaseProvider):
    """
    OpenAI API provider.

    Capabilities:
    - Chat completions
    - Embeddings
    - Function calling
    - Vision support
    """

    def __init__(
        self,
        config: ProviderConfig,
        transport: BaseTransport,
        rate_limiter: BaseRateLimiter
    ):
        super().__init__(config, transport, rate_limiter)

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with API key"""
        headers = {
            "Authorization": f"Bearer {self.config.api_key_env}",
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
        Send chat completion request to OpenAI.

        Args:
            messages: List of conversation messages
            model: Model name (defaults to config default)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            tools: Tool definitions for function calling

        Returns:
            ModelResponse with completion
        """
        model = model or self.config.default_model

        # Acquire rate limit clearance
        estimated_tokens = sum(self._estimate_tokens(m.content) for m in messages)
        if not await self.rate_limiter.acquire(tokens=estimated_tokens):
            raise ProviderRateLimitError(self.name, retry_after=60)

        # Build request
        endpoint = f"{self.config.endpoint}/chat/completions"
        request_body: Dict[str, Any] = {
            "model": model,
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
        Stream chat completion from OpenAI.

        Yields:
            Content delta strings as they arrive
        """
        model = model or self.config.default_model

        # Build request
        endpoint = f"{self.config.endpoint}/chat/completions"
        request_body: Dict[str, Any] = {
            "model": model,
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

        # Stream response
        async for chunk in self._stream_request(request_body, endpoint):
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
        """Parse OpenAI API response"""
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

    async def embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[List[float]]:
        """
        Get embeddings for texts.

        Args:
            texts: List of texts to embed
            model: Embedding model name

        Returns:
            List of embedding vectors
        """
        model = model or "text-embedding-3-small"
        endpoint = f"{self.config.endpoint}/embeddings"

        request_body = {
            "model": model,
            "input": texts,
        }

        response = await self.transport.send(
            request_body,
            endpoint,
            headers=self._get_headers()
        )

        return [item["embedding"] for item in response.get("data", [])]

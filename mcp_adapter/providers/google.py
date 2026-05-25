"""
Google Provider Adapter

Implements the Google AI (Gemini) API integration for completions,
function calling, and batch processing.

Endpoint: https://generativelanguage.googleapis.com/v1/*
"""

from typing import Dict, Any, Optional, List, AsyncIterator

from mcp_adapter.config import ProviderConfig
from mcp_adapter.transport import BaseTransport
from mcp_adapter.rate_limiter import RateLimiter as BaseRateLimiter
from mcp_adapter.providers.base import (
    BaseProvider, ModelResponse, Message, ToolDefinition, ToolCall
)
from mcp_adapter.exceptions import ProviderAuthError, ProviderRateLimitError


class GoogleProvider(BaseProvider):
    """
    Google Generative AI provider.

    Capabilities:
    - Gemini completions
    - Function calling
    - Batch processing
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
        Send completion request to Google Gemini.

        Args:
            messages: List of conversation messages
            model: Model name (defaults to config default)
            temperature: Sampling temperature
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

        # Build request - Gemini uses a different format
        endpoint = f"{self.config.endpoint}/models/{model}:generateContent"

        # Convert messages to Gemini format
        contents = self._convert_to_gemini_format(messages)

        request_body: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
            }
        }

        if max_tokens:
            request_body["generationConfig"]["maxOutputTokens"] = max_tokens

        if tools:
            request_body["tools"] = self._convert_tools(tools)

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
        Stream completion from Google Gemini.

        Yields:
            Content delta strings as they arrive
        """
        model = model or self.config.default_model
        endpoint = f"{self.config.endpoint}/models/{model}:streamGenerateContent"

        contents = self._convert_to_gemini_format(messages)

        request_body: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
            }
        }

        if max_tokens:
            request_body["generationConfig"]["maxOutputTokens"] = max_tokens

        if tools:
            request_body["tools"] = self._convert_tools(tools)

        request_body.update(kwargs)

        # For streaming, we would use StreamingTransport
        response = await self.transport.send(request_body, endpoint, headers=self._get_headers())

        if "candidates" in response:
            for candidate in response["candidates"]:
                content = candidate.get("content", {})
                parts = content.get("parts", [])
                for part in parts:
                    if "text" in part:
                        yield part["text"]

    def _convert_to_gemini_format(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert messages to Gemini format"""
        contents = []
        for msg in messages:
            role = "user" if msg.role.value in ("user", "tool") else "model"
            if msg.role.value == "system":
                # System messages go in system instruction
                continue

            content = {
                "role": role,
                "parts": [{"text": msg.content}]
            }

            # Handle tool results
            if msg.role.value == "tool":
                content["parts"] = [{"functionResponse": {
                    "name": msg.name,
                    "response": {"result": msg.content}
                }}]

            contents.append(content)

        return contents

    def _convert_tools(self, tools: List[ToolDefinition]) -> Dict[str, Any]:
        """Convert tools to Gemini format"""
        return {
            "functionDeclarations": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
                for tool in tools
            ]
        }

    def _parse_response(self, response: Dict[str, Any], model: str) -> ModelResponse:
        """Parse Gemini API response"""
        candidates = response.get("candidates", [])
        if not candidates:
            raise Exception("No candidates in response")

        candidate = candidates[0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])

        text_parts = []
        tool_calls = []

        for part in parts:
            if "text" in part:
                text_parts.append(part["text"])
            elif "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append(ToolCall(
                    id=str(id(fc)),  # Gemini doesn't have IDs like OpenAI
                    name=fc.get("name", ""),
                    arguments=fc.get("args", {})
                ))

        return ModelResponse(
            content="".join(text_parts),
            model=model,
            finish_reason=candidate.get("finishReason"),
            tool_calls=tool_calls,
            usage=response.get("usageMetadata", {}),
            raw_response=response
        )

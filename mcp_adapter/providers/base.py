"""
Base Provider Interface

Defines the abstract base class and data models for all AI providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List, AsyncIterator

from mcp_adapter.config import ProviderConfig
from mcp_adapter.transport import BaseTransport
from mcp_adapter.rate_limiter import RateLimiter as BaseRateLimiter


class MessageRole(Enum):
    """Message role in a conversation"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """A message in a conversation"""
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


@dataclass
class ToolDefinition:
    """Definition of a tool the model can call"""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)


@dataclass
class ToolCall:
    """A tool call made by the model"""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ModelResponse:
    """Response from a model"""
    content: str
    model: str
    finish_reason: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    usage: Dict[str, int] = field(default_factory=dict)
    raw_response: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.content


@dataclass
class StreamChunk:
    """A chunk in a streaming response"""
    content: str
    delta: str
    is_complete: bool = False
    finish_reason: Optional[str] = None


class BaseProvider(ABC):
    """
    Abstract base class for AI providers.

    All provider implementations must inherit from this class
    and implement the required methods.
    """

    def __init__(
        self,
        config: ProviderConfig,
        transport: BaseTransport,
        rate_limiter: "BaseRateLimiter"
    ):
        self.config = config
        self.transport = transport
        self.rate_limiter = rate_limiter
        self._capabilities: List[str] = config.capabilities

    @property
    def capabilities(self) -> List[str]:
        """List of provider capabilities"""
        return self._capabilities

    @property
    def name(self) -> str:
        """Provider name"""
        return self.config.name

    @property
    def endpoint(self) -> str:
        """API endpoint"""
        return self.config.endpoint

    @abstractmethod
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
        Send a completion request.

        Args:
            messages: Conversation messages
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            tools: Available tools for function calling

        Returns:
            ModelResponse
        """
        pass

    @abstractmethod
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
        Stream a completion response.

        Args:
            messages: Conversation messages
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            tools: Available tools for function calling

        Yields:
            Content chunks as they arrive
        """
        pass

    async def close(self) -> None:
        """Close provider connections"""
        await self.transport.close()

    def _prepare_messages(
        self,
        messages: List[Message]
    ) -> List[Dict[str, Any]]:
        """Convert Message objects to provider format"""
        return [
            {
                "role": msg.role.value,
                "content": msg.content,
                **({"name": msg.name} if msg.name else {}),
                **({"tool_call_id": msg.tool_call_id} if msg.tool_call_id else {}),
            }
            for msg in messages
        ]

    def _parse_tool_calls(
        self,
        raw_calls: List[Dict[str, Any]]
    ) -> List[ToolCall]:
        """Parse raw tool calls into ToolCall objects"""
        return [
            ToolCall(
                id=call.get("id", ""),
                name=call.get("name", ""),
                arguments=call.get("arguments", {})
            )
            for call in raw_calls
        ]

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (actual count varies by model)"""
        # Approximate: 1 token ≈ 4 characters for English
        return len(text) // 4

"""
MCP Adapter - Model Context Protocol Adapter for AI Business Runtime Framework

This module provides communication between the runtime framework and external
AI models and services through a standardized MCP interface.
"""

from mcp_adapter.protocol import ProtocolHandler
from mcp_adapter.transport import HTTPTransport, WebSocketTransport
from mcp_adapter.providers import OpenAIProvider, AnthropicProvider, GoogleProvider, CustomProvider
from mcp_adapter.exceptions import MCPError, ErrorCode

__version__ = "1.0.0"

__all__ = [
    "ProtocolHandler",
    "HTTPTransport",
    "WebSocketTransport",
    "OpenAIProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "CustomProvider",
    "MCPError",
    "ErrorCode",
]

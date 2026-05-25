"""
MCP Error Codes and Exception Classes
"""

from enum import IntEnum
from typing import Optional, Dict, Any


class ErrorCode(IntEnum):
    """MCP protocol error codes"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    PROVIDER_AUTH_FAILED = -32000
    PROVIDER_RATE_LIMITED = -32001
    PROVIDER_RESOURCE_EXHAUSTED = -32002


class MCPError(Exception):
    """Base MCP exception"""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "code": self.code.value,
            "message": self.message
        }
        if self.data:
            result["data"] = self.data
        return result


class ParseError(MCPError):
    """Invalid JSON in request"""

    def __init__(self, message: str = "Invalid JSON", data: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCode.PARSE_ERROR, message, data)


class InvalidRequest(MCPError):
    """Request is malformed or missing required fields"""

    def __init__(self, message: str = "Invalid request", data: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCode.INVALID_REQUEST, message, data)


class MethodNotFound(MCPError):
    """Requested method is not supported"""

    def __init__(self, method: str, data: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCode.METHOD_NOT_FOUND, f"Method not found: {method}", data)


class InvalidParams(MCPError):
    """Invalid parameters for method"""

    def __init__(self, message: str = "Invalid parameters", data: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCode.INVALID_PARAMS, message, data)


class ProviderAuthError(MCPError):
    """Provider authentication failed"""

    def __init__(self, provider: str, message: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        msg = message or f"{provider} authentication failed"
        super().__init__(ErrorCode.PROVIDER_AUTH_FAILED, msg, data)


class ProviderRateLimitError(MCPError):
    """Provider rate limit exceeded"""

    def __init__(self, provider: str, retry_after: Optional[int] = None, data: Optional[Dict[str, Any]] = None):
        msg = f"{provider} rate limit exceeded"
        if retry_after:
            msg += f", retry after {retry_after}s"
        super().__init__(ErrorCode.PROVIDER_RATE_LIMITED, msg, data)


class ProviderResourceError(MCPError):
    """Provider resource exhausted"""

    def __init__(self, provider: str, message: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        msg = message or f"{provider} resource exhausted"
        super().__init__(ErrorCode.PROVIDER_RESOURCE_EXHAUSTED, msg, data)


class TransportError(MCPError):
    """Transport-level error"""

    def __init__(self, message: str, data: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCode.INTERNAL_ERROR, message, data)


class RetryableError(MCPError):
    """Error that can be retried"""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        retry_after: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(code, message, data)
        self.retry_after = retry_after

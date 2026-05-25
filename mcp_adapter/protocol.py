"""
MCP Protocol Handler

Implements request building, response parsing, and error handling
for the Model Context Protocol.
"""

import json
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum

from mcp_adapter.exceptions import (
    ParseError, InvalidRequest, MethodNotFound,
    InvalidParams, MCPError, ErrorCode
)


class MessageType(Enum):
    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"
    NOTIFICATION = "notification"


@dataclass
class MCPRequest:
    jsonrpc: str = "2.0"
    method: str = ""
    params: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None


@dataclass
class MCPResponse:
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None


class ProtocolHandler:
    """
    Handles MCP protocol request/response communication.
    """

    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self._request_count = 0

    def build_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        request_id: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Build a properly formatted MCP request.

        Args:
            method: The RPC method name
            params: Method parameters
            request_id: Optional request identifier

        Returns:
            Formatted MCP request dictionary
        """
        self._request_count += 1

        request = MCPRequest(
            jsonrpc="2.0",
            method=method,
            params=params or {},
            id=request_id or self._request_count
        )

        return self._serialize_request(request)

    def _serialize_request(self, request: MCPRequest) -> Dict[str, Any]:
        """Serialize MCPRequest to dictionary"""
        result = {
            "jsonrpc": request.jsonrpc,
            "method": request.method
        }

        if request.params:
            result["params"] = request.params
        if request.id is not None:
            result["id"] = request.id

        return result

    def parse_response(
        self,
        response_data: Dict[str, Any]
    ) -> MCPResponse:
        """
        Parse an MCP response from provider.

        Args:
            response_data: Raw response dictionary

        Returns:
            Parsed MCPResponse object

        Raises:
            ParseError: If response is invalid JSON
            InvalidRequest: If response structure is invalid
        """
        try:
            if not isinstance(response_data, dict):
                raise ParseError(f"Expected object, got {type(response_data).__name__}")

            jsonrpc = response_data.get("jsonrpc")
            if jsonrpc != "2.0":
                raise InvalidRequest(f"Invalid JSON-RPC version: {jsonrpc}")

            response = MCPResponse(
                jsonrpc=jsonrpc,
                id=response_data.get("id"),
                result=response_data.get("result"),
                error=response_data.get("error")
            )

            self._validate_response(response)
            return response

        except json.JSONDecodeError as e:
            raise ParseError(f"Invalid JSON: {str(e)}")

    def _validate_response(self, response: MCPResponse) -> None:
        """Validate response structure"""
        if response.result is None and response.error is None:
            raise InvalidRequest("Response must have either 'result' or 'error'")

        if response.error is not None:
            if not isinstance(response.error, dict):
                raise InvalidRequest("Error must be an object")
            if "code" not in response.error or "message" not in response.error:
                raise InvalidRequest("Error must have 'code' and 'message'")

    def build_error_response(
        self,
        error: MCPError,
        request_id: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Build an MCP error response.

        Args:
            error: The MCP error
            request_id: Request identifier for correlation

        Returns:
            Formatted error response
        """
        return {
            "jsonrpc": "2.0",
            "error": error.to_dict(),
            "id": request_id
        }

    def parse_error(self, error_data: Any) -> MCPError:
        """
        Parse error data into MCPError.

        Args:
            error_data: Raw error data

        Returns:
            Appropriate MCPError subclass
        """
        if isinstance(error_data, dict):
            code = error_data.get("code", ErrorCode.INTERNAL_ERROR)
            message = error_data.get("message", "Unknown error")
            data = error_data.get("data")

            try:
                error_code = ErrorCode(code)
            except ValueError:
                error_code = ErrorCode.INTERNAL_ERROR

            return MCPError(error_code, message, data)

        return MCPError(ErrorCode.INTERNAL_ERROR, str(error_data))

    def should_retry(self, error: MCPError) -> bool:
        """
        Determine if a request should be retried based on error.

        Args:
            error: The error to evaluate

        Returns:
            True if the request should be retried
        """
        retryable_codes = {
            ErrorCode.PARSE_ERROR,
            ErrorCode.INTERNAL_ERROR,
            ErrorCode.PROVIDER_RATE_LIMITED,
            ErrorCode.PROVIDER_RESOURCE_EXHAUSTED,
        }
        return error.code in retryable_codes

    def get_retry_after(self, error: MCPError) -> Optional[int]:
        """
        Get recommended retry delay from error.

        Args:
            error: The error

        Returns:
            Seconds to wait before retry, or None
        """
        if isinstance(error, RetryableError):
            return error.retry_after
        return None

    def build_batch_request(
        self,
        requests: List[Dict[str, Any]]
    ) -> str:
        """
        Build a batch request (JSON array).

        Args:
            requests: List of request objects

        Returns:
            JSON string of batch request
        """
        return json.dumps(requests)

    def parse_batch_response(
        self,
        response_text: str
    ) -> List[MCPResponse]:
        """
        Parse a batch response (JSON array).

        Args:
            response_text: Raw response text

        Returns:
            List of MCPResponse objects
        """
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ParseError(f"Invalid JSON: {str(e)}")

        if not isinstance(data, list):
            raise InvalidRequest("Batch response must be an array")

        return [self.parse_response(item) for item in data]

    def create_progress_notification(
        self,
        method: str,
        progress: float,
        total: float,
        request_id: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Create a progress notification (for streaming).

        Args:
            method: Original method name
            progress: Current progress value
            total: Total value
            request_id: Associated request ID

        Returns:
            Progress notification object
        """
        return {
            "jsonrpc": "2.0",
            "method": "$/progress",
            "params": {
                "method": method,
                "progress": progress,
                "total": total
            },
            "id": request_id
        }


# Import for type checking
from mcp_adapter.exceptions import RetryableError

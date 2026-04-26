# mcp/protocol.py
"""MCP JSON-RPC protocol implementation.

Implements the Model Context Protocol (MCP) JSON-RPC 2.0 specification.
This module handles:
- JSON-RPC 2.0 request/response formatting
- MCP-specific method signatures
- Error handling and validation
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import structlog

logger = structlog.get_logger()


class MCPErrorCode(Enum):
    """MCP-specific error codes."""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_ERROR = -32000


@dataclass
class JSONRPCRequest:
    """JSON-RPC 2.0 request."""
    jsonrpc: str = "2.0"
    id: str = ""
    method: str = ""
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": self.method,
            "params": self.params,
        }


@dataclass
class JSONRPCResponse:
    """JSON-RPC 2.0 response."""
    jsonrpc: str = "2.0"
    id: str = ""
    result: Optional[Any] = None
    error: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
        }
        if self.error is not None:
            data["error"] = self.error
        else:
            data["result"] = self.result
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JSONRPCResponse":
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id", ""),
            result=data.get("result"),
            error=data.get("error"),
        )


@dataclass
class MCPInitializeParams:
    """MCP initialize method parameters."""
    protocolVersion: str = "2024-11-05"
    capabilities: dict[str, Any] = field(default_factory=dict)
    clientInfo: dict[str, str] = field(default_factory=dict)


@dataclass
class MCPInitializeResult:
    """MCP initialize method result."""
    protocolVersion: str = "2024-11-05"
    capabilities: dict[str, Any] = field(default_factory=dict)
    serverInfo: dict[str, str] = field(default_factory=dict)


@dataclass
class MCPToolCallParams:
    """MCP tools/call method parameters."""
    name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPToolCallResult:
    """MCP tools/call method result."""
    content: Any = None
    isError: bool = False


class MCPProtocol:
    """MCP JSON-RPC protocol handler."""

    @staticmethod
    def create_initialize_request(
        client_name: str = "OpenAGI",
        client_version: str = "5.0.0",
        capabilities: Optional[dict[str, Any]] = None,
    ) -> JSONRPCRequest:
        """Create an initialize request."""
        return JSONRPCRequest(
            id="init",
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": capabilities or {"tools": {}},
                "clientInfo": {
                    "name": client_name,
                    "version": client_version,
                },
            },
        )

    @staticmethod
    def create_tool_call_request(
        tool_name: str,
        arguments: dict[str, Any],
        request_id: Optional[str] = None,
    ) -> JSONRPCRequest:
        """Create a tools/call request."""
        return JSONRPCRequest(
            id=request_id or "",
            method="tools/call",
            params={
                "name": tool_name,
                "arguments": arguments,
            },
        )

    @staticmethod
    def parse_response(response_text: str) -> Optional[JSONRPCResponse]:
        """Parse a JSON-RPC response."""
        try:
            data = json.loads(response_text)
            return JSONRPCResponse.from_dict(data)
        except json.JSONDecodeError as e:
            logger.error("mcp.protocol.parse_error", error=str(e))
            return None

    @staticmethod
    def create_error_response(
        request_id: str,
        code: int,
        message: str,
        data: Optional[Any] = None,
    ) -> JSONRPCResponse:
        """Create an error response."""
        return JSONRPCResponse(
            id=request_id,
            error={
                "code": code,
                "message": message,
                "data": data,
            },
        )

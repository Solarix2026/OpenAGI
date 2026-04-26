# mcp/hub.py
"""MCP Hub — manages all connected MCP servers.

The hub is the bridge between external MCP servers and the ToolRegistry.
When a new MCP server is connected:
1. Handshake and capability discovery
2. Each MCP tool is wrapped in an MCPToolAdapter (implements BaseTool)
3. Adapters are registered in ToolRegistry
4. Agent can now invoke MCP tools via standard registry.invoke()

No MCP tool names are hardcoded. Zero hardcoded server lists.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import uuid4

import httpx
import structlog

from tools.base_tool import BaseTool, ToolMeta, ToolResult
from tools.registry import ToolRegistry

logger = structlog.get_logger()


@dataclass
class MCPServerInfo:
    """Information about a connected MCP server."""
    server_id: str
    name: str
    url: str
    version: str = "1.0.0"
    protocol: str = "http"   # "http" | "stdio"
    tools: list[dict] = field(default_factory=list)
    connected: bool = False


class MCPToolAdapter(BaseTool):
    """Wraps an MCP tool call as a BaseTool for the registry."""

    def __init__(
        self,
        server: MCPServerInfo,
        tool_def: dict,
        http_client: httpx.AsyncClient,
    ) -> None:
        self._server = server
        self._tool_def = tool_def
        self._client = http_client

    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name=f"{self._server.name}.{self._tool_def['name']}",
            description=self._tool_def.get("description", ""),
            parameters=self._tool_def.get("inputSchema", {"type": "object"}),
            risk_score=0.3,
            categories=["mcp", self._server.name],
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Call the MCP tool via JSON-RPC."""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": str(uuid4()),
                "method": "tools/call",
                "params": {
                    "name": self._tool_def["name"],
                    "arguments": kwargs,
                },
            }

            response = await self._client.post(
                f"{self._server.url}/rpc",
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                return ToolResult(
                    success=False,
                    tool_name=self.meta.name,
                    error=str(data["error"]),
                )

            result = data.get("result", {})
            content = result.get("content", result)

            return ToolResult(
                success=True,
                tool_name=self.meta.name,
                data=content,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.meta.name,
                error=str(e),
            )


class MCPHub:
    """
    Central manager for MCP server connections.

    Usage:
        hub = MCPHub(tool_registry=registry)
        await hub.connect("http://localhost:3000", server_name="filesystem")
        # → filesystem tools now in registry
    """

    def __init__(self, tool_registry: Optional[ToolRegistry] = None) -> None:
        self._registry = tool_registry
        self._servers: dict[str, MCPServerInfo] = {}
        self._client = httpx.AsyncClient(timeout=30)

    async def connect(
        self,
        url: str,
        server_name: Optional[str] = None,
        protocol: str = "http",
    ) -> str:
        """Connect to an MCP server and register its tools."""
        server_id = str(uuid4())[:8]

        # Handshake
        info = await self._handshake(url)
        if not info:
            raise ConnectionError(f"Failed to connect to MCP server at {url}")

        name = server_name or info.get("name", f"mcp-{server_id}")
        tools = info.get("capabilities", {}).get("tools", [])

        server = MCPServerInfo(
            server_id=server_id,
            name=name,
            url=url,
            version=info.get("version", "1.0.0"),
            protocol=protocol,
            tools=tools,
            connected=True,
        )

        self._servers[server_id] = server

        # Register tools in ToolRegistry
        if self._registry:
            for tool_def in tools:
                adapter = MCPToolAdapter(server, tool_def, self._client)
                self._registry.register(adapter)
                logger.info("mcp.tool_registered", name=adapter.meta.name)

        logger.info("mcp.server_connected", name=name, tools=len(tools))
        return server_id

    async def disconnect(self, server_id: str) -> bool:
        """Disconnect server and unregister its tools."""
        server = self._servers.get(server_id)
        if not server:
            return False

        if self._registry:
            for tool_def in server.tools:
                tool_name = f"{server.name}.{tool_def['name']}"
                self._registry.unregister(tool_name)

        server.connected = False
        del self._servers[server_id]
        logger.info("mcp.server_disconnected", name=server.name)
        return True

    async def _handshake(self, url: str) -> Optional[dict]:
        """MCP initialization handshake."""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": "init",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "OpenAGI", "version": "5.0.0"},
                },
            }
            response = await self._client.post(
                f"{url}/rpc", json=payload, timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get("result")
        except Exception as e:
            logger.warning("mcp.handshake_failed", url=url, error=str(e))
            return None

    def list_servers(self) -> list[MCPServerInfo]:
        """List all connected servers."""
        return list(self._servers.values())

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

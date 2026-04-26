# mcp/__init__.py
"""MCP Hub — Self-configuring MCP server management."""
from mcp.hub import MCPHub, MCPToolAdapter, MCPServerInfo
from mcp.auto_discover import MCPAutoDiscover, KNOWN_MCP_SERVERS

__all__ = [
    "MCPHub",
    "MCPToolAdapter",
    "MCPServerInfo",
    "MCPAutoDiscover",
    "KNOWN_MCP_SERVERS",
]

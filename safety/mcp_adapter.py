# Copyright (c) 2026 HackerTMJ
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/HackerTMJ/OpenAGI

"""
mcp_adapter.py — MCP (Model Context Protocol) server adapter

HTTP/SSE adapter for MCP servers.
- connect(url, name) → store connection
- list_tools(server) → GET /tools
- call_tool(server, tool, params) → POST /tools/{name}
- register_mcp_tools_to_registry(registry) → auto-register all with prefix mcp_{server}_{tool}

MCP is Anthropic's open protocol for context exchange between AI systems.
"""
import logging
import requests
import json
from typing import Optional

log = logging.getLogger("MCP")


class MCPAdapter:
    def __init__(self):
        self._connections: dict[str, dict] = {}

    def connect(self, url: str, name: str) -> dict:
        """Connect to an MCP server and store its info."""
        try:
            # Try to get server info
            resp = requests.get(f"{url}/info", timeout=10)
            info = resp.json() if resp.status_code == 200 else {}
            self._connections[name] = {"url": url, "info": info}
            log.info(f"[MCP] Connected to {name} at {url}")
            return {"success": True, "name": name, "info": info}
        except Exception as e:
            log.error(f"[MCP] Failed to connect to {name}: {e}")
            return {"success": False, "error": str(e)}

    def list_tools(self, server: str) -> list:
        """List tools available on an MCP server."""
        conn = self._connections.get(server)
        if not conn:
            return []
        try:
            resp = requests.get(f"{conn['url']}/tools", timeout=10)
            if resp.status_code == 200:
                return resp.json().get("tools", [])
        except Exception as e:
            log.debug(f"[MCP] Failed to list tools from {server}: {e}")
        return []

    def call_tool(self, server: str, tool: str, params: dict) -> dict:
        """Call a tool on an MCP server."""
        conn = self._connections.get(server)
        if not conn:
            return {"success": False, "error": f"Server {server} not connected"}
        try:
            resp = requests.post(
                f"{conn['url']}/tools/{tool}",
                json={"params": params},
                timeout=30
            )
            return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def register_mcp_tools_to_registry(self, registry):
        """Auto-discover and register all MCP tools to local registry."""
        for server_name, conn in self._connections.items():
            tools = self.list_tools(server_name)
            for tool in tools:
                tool_name = f"mcp_{server_name}_{tool['name']}"

                def make_tool_caller(srv=server_name, t=tool['name']):
                    def caller(params):
                        return self.call_tool(srv, t, params)
                    return caller

                registry.register(
                    name=tool_name,
                    func=make_tool_caller(),
                    description=f"[MCP:{server_name}] {tool.get('description', '')}",
                    parameters=tool.get("parameters", {}),
                    category="mcp"
                )
            log.info(f"[MCP] Registered {len(tools)} tools from {server_name}")

    def disconnect(self, name: str) -> bool:
        """Disconnect from an MCP server."""
        if name in self._connections:
            del self._connections[name]
            log.info(f"[MCP] Disconnected from {name}")
            return True
        return False

    def list_servers(self) -> list[str]:
        """List all connected MCP servers."""
        return list(self._connections.keys())

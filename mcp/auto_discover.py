# mcp/auto_discover.py
"""MCP Auto-Discovery — find MCP servers by name or description.

Known registry: https://mcpservers.org (or internal list)
Fallback: LLM suggests likely server + install command

This is the "intelligence" layer: user says "connect to GitHub"
and the system figures out the right server URL and protocol.
"""
from __future__ import annotations

from typing import Optional
import httpx
import structlog

logger = structlog.get_logger()

# Well-known MCP servers (not hardcoded for tools — hardcoded for REGISTRY only)
KNOWN_MCP_SERVERS = {
    "filesystem":    {"url": None, "install": "npx @modelcontextprotocol/server-filesystem"},
    "github":        {"url": None, "install": "npx @modelcontextprotocol/server-github"},
    "google-drive":  {"url": "https://drivemcp.googleapis.com/mcp/v1", "install": None},
    "gmail":         {"url": "https://gmailmcp.googleapis.com/mcp/v1", "install": None},
    "google-calendar": {"url": "https://calendarmcp.googleapis.com/mcp/v1", "install": None},
    "notion":        {"url": None, "install": "npx @notionhq/notion-mcp-server"},
    "postgres":      {"url": None, "install": "npx @modelcontextprotocol/server-postgres"},
    "slack":         {"url": None, "install": "npx @modelcontextprotocol/server-slack"},
    "brave-search":  {"url": None, "install": "npx @modelcontextprotocol/server-brave-search"},
    "puppeteer":     {"url": None, "install": "npx @modelcontextprotocol/server-puppeteer"},
}


class MCPAutoDiscover:
    """
    Discovers MCP server info from a name or description.

    Priority:
    1. Check known registry
    2. Search MCP registry API
    3. LLM suggests based on description
    """

    async def find(self, query: str) -> Optional[dict]:
        """Find MCP server info by name or description."""
        query_lower = query.lower().strip()

        # 1. Exact match in known registry
        if query_lower in KNOWN_MCP_SERVERS:
            return {"name": query_lower, **KNOWN_MCP_SERVERS[query_lower]}

        # 2. Partial match
        for name, info in KNOWN_MCP_SERVERS.items():
            if query_lower in name or name in query_lower:
                return {"name": name, **info}

        # 3. Search MCP registry (future: https://mcpservers.org/api)
        result = await self._search_registry(query)
        if result:
            return result

        # 4. Return None — caller should ask LLM for suggestions
        return None

    async def _search_registry(self, query: str) -> Optional[dict]:
        """Search the MCP server registry."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # MCP registry search (placeholder — use actual registry when available)
                response = await client.get(
                    "https://mcpservers.org/api/search",
                    params={"q": query},
                    timeout=5,
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("results"):
                        first = data["results"][0]
                        return {
                            "name": first["name"],
                            "url": first.get("url"),
                            "install": first.get("npm_package"),
                        }
        except Exception:
            pass
        return None

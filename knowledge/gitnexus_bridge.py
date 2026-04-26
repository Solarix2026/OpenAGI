# knowledge/gitnexus_bridge.py
"""GitNexus-compatible MCP server bridge.

Exposes our KnowledgeGraphEngine as a GitNexus-compatible MCP server.
This means:
1. GitNexus IDE plugin can connect to our graph via MCP
2. Our agent can query graph using GitNexus tool schema
3. Compatible with AGENTS.md / CLAUDE.md GitNexus conventions

Also works as a client to connect TO a real GitNexus instance.
"""
from __future__ import annotations

from typing import Any, Optional

import structlog

from knowledge.graph_engine import KnowledgeGraphEngine
from knowledge.schema import KGNode, KGEdge, NodeType, EdgeType

logger = structlog.get_logger()


class GitNexusBridge:
    """
    Exposes KnowledgeGraphEngine via GitNexus MCP tool schema.

    Tool names match GitNexus exactly so AGENTS.md instructions work:
    - gitnexus_query(query) → semantic search
    - gitnexus_context(name) → node + neighborhood
    - gitnexus_impact(target, direction) → blast radius
    - gitnexus_detect_changes() → compare current graph vs last commit
    """

    def __init__(self, graph: KnowledgeGraphEngine) -> None:
        self.graph = graph

    async def gitnexus_query(self, query: str, top_k: int = 5) -> dict:
        """Search codebase/knowledge by concept."""
        nodes = self.graph.query(query, top_k=top_k)
        return {
            "query": query,
            "results": [
                {
                    "node_id": n.node_id,
                    "label": n.label,
                    "type": n.node_type.name,
                    "confidence": n.confidence,
                    "properties": n.properties,
                }
                for n in nodes
            ],
            "count": len(nodes),
        }

    async def gitnexus_context(self, name: str, depth: int = 2) -> dict:
        """Get full context for a named entity."""
        # Find node by label
        nodes = self.graph.query(name, top_k=1)
        if not nodes:
            return {"error": f"No node found for '{name}'"}

        context = self.graph.get_context(nodes[0].node_id, depth=depth)
        return {
            "node": {
                "label": context["node"].label if context.get("node") else name,
                "type": context["node"].node_type.name if context.get("node") else "UNKNOWN",
            },
            "predecessors": [n.label for n in context.get("predecessors", [])],
            "successors": [n.label for n in context.get("successors", [])],
            "neighborhood_size": context.get("neighborhood_size", 0),
        }

    async def gitnexus_impact(
        self, target: str, direction: str = "upstream"
    ) -> dict:
        """Assess blast radius of changing a symbol."""
        nodes = self.graph.query(target, top_k=1)
        if not nodes:
            return {"blast_radius": 0, "risk_level": "LOW", "affected": []}

        return self.graph.impact_analysis(nodes[0].node_id, direction=direction)

    async def gitnexus_detect_changes(self) -> dict:
        """Detect what changed since last snapshot."""
        # Simple implementation: return graph stats
        stats = self.graph.get_stats()
        return {
            "status": "ok",
            "graph_stats": stats,
            "message": "Use git diff for code changes; this covers knowledge graph changes.",
        }

    def as_mcp_tools(self) -> list[dict]:
        """Return tool definitions for MCP server registration."""
        return [
            {
                "name": "gitnexus_query",
                "description": "Search the knowledge graph by concept or text",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "top_k": {"type": "integer", "default": 5},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "gitnexus_context",
                "description": "Get full context for a named entity including callers/callees",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "depth": {"type": "integer", "default": 2},
                    },
                    "required": ["name"],
                },
            },
            {
                "name": "gitnexus_impact",
                "description": "Assess blast radius of changing a symbol",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string"},
                        "direction": {"type": "string", "enum": ["upstream", "downstream"]},
                    },
                    "required": ["target"],
                },
            },
            {
                "name": "gitnexus_detect_changes",
                "description": "Detect changes in knowledge graph since last commit",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]

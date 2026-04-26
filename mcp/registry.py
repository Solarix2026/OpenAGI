# mcp/registry.py
"""MCP Server Registry — tracks connected MCP servers.

Maintains a registry of all connected MCP servers with their:
- Connection status
- Capabilities
- Tool mappings
- Metadata

This is separate from ToolRegistry — this tracks MCP servers,
while ToolRegistry tracks individual tools (including MCP-wrapped tools).
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import structlog

from mcp.hub import MCPServerInfo

logger = structlog.get_logger()


@dataclass
class MCPServerEntry:
    """A registry entry for an MCP server."""
    server_id: str
    name: str
    url: str
    version: str = "1.0.0"
    protocol: str = "http"
    connected: bool = False
    capabilities: dict[str, Any] = field(default_factory=dict)
    tool_count: int = 0
    last_connected: Optional[str] = None
    last_error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class MCPServerRegistry:
    """
    Registry for MCP server connections.

    Provides:
    - Persistent storage of server configurations
    - Connection history tracking
    - Server metadata management
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or Path(".memory/mcp_registry.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: dict[str, MCPServerEntry] = {}
        self._init_db()
        self._load_from_db()

    def _init_db(self) -> None:
        """Initialize SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mcp_servers (
                    server_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    version TEXT,
                    protocol TEXT,
                    connected INTEGER,
                    capabilities_json TEXT,
                    tool_count INTEGER,
                    last_connected TEXT,
                    last_error TEXT,
                    metadata_json TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_mcp_name
                ON mcp_servers(name)
            """)

    def _load_from_db(self) -> None:
        """Load entries from database."""
        with sqlite3.connect(self.db_path) as conn:
            for row in conn.execute("SELECT * FROM mcp_servers"):
                entry = MCPServerEntry(
                    server_id=row[0],
                    name=row[1],
                    url=row[2],
                    version=row[3] or "1.0.0",
                    protocol=row[4] or "http",
                    connected=bool(row[5]),
                    capabilities=json.loads(row[6]) if row[6] else {},
                    tool_count=row[7] or 0,
                    last_connected=row[8],
                    last_error=row[9],
                    metadata=json.loads(row[10]) if row[10] else {},
                )
                self._entries[entry.server_id] = entry

    def register(self, server: MCPServerInfo) -> MCPServerEntry:
        """Register or update a server entry."""
        entry = MCPServerEntry(
            server_id=server.server_id,
            name=server.name,
            url=server.url,
            version=server.version,
            protocol=server.protocol,
            connected=server.connected,
            capabilities={"tools": server.tools},
            tool_count=len(server.tools),
            last_connected=datetime.utcnow().isoformat() if server.connected else None,
        )

        self._entries[server.server_id] = entry
        self._save_entry(entry)

        logger.info("mcp.registry.registered", name=server.name, server_id=server.server_id)
        return entry

    def update_connection_status(
        self,
        server_id: str,
        connected: bool,
        error: Optional[str] = None,
    ) -> bool:
        """Update connection status for a server."""
        if server_id not in self._entries:
            return False

        entry = self._entries[server_id]
        entry.connected = connected
        entry.last_connected = datetime.utcnow().isoformat() if connected else None
        entry.last_error = error

        self._save_entry(entry)
        return True

    def get(self, server_id: str) -> Optional[MCPServerEntry]:
        """Get a server entry by ID."""
        return self._entries.get(server_id)

    def get_by_name(self, name: str) -> Optional[MCPServerEntry]:
        """Get a server entry by name."""
        for entry in self._entries.values():
            if entry.name == name:
                return entry
        return None

    def list_all(self) -> list[MCPServerEntry]:
        """List all server entries."""
        return list(self._entries.values())

    def list_connected(self) -> list[MCPServerEntry]:
        """List only connected servers."""
        return [e for e in self._entries.values() if e.connected]

    def remove(self, server_id: str) -> bool:
        """Remove a server entry."""
        if server_id not in self._entries:
            return False

        del self._entries[server_id]

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM mcp_servers WHERE server_id = ?", (server_id,))

        logger.info("mcp.registry.removed", server_id=server_id)
        return True

    def _save_entry(self, entry: MCPServerEntry) -> None:
        """Save entry to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO mcp_servers
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.server_id,
                    entry.name,
                    entry.url,
                    entry.version,
                    entry.protocol,
                    int(entry.connected),
                    json.dumps(entry.capabilities),
                    entry.tool_count,
                    entry.last_connected,
                    entry.last_error,
                    json.dumps(entry.metadata),
                ),
            )

    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        total = len(self._entries)
        connected = sum(1 for e in self._entries.values() if e.connected)
        total_tools = sum(e.tool_count for e in self._entries.values())

        return {
            "total_servers": total,
            "connected_servers": connected,
            "disconnected_servers": total - connected,
            "total_tools": total_tools,
        }

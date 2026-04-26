# tests/mcp/test_hub.py
"""Tests for MCP Hub - self-configuring MCP server management."""
import pytest
from unittest.mock import AsyncMock, patch
from mcp.hub import MCPHub
from mcp.auto_discover import MCPAutoDiscover


@pytest.mark.asyncio
async def test_hub_connects_to_server():
    """Test that MCP Hub can connect to a server."""
    hub = MCPHub()
    mock_server_info = {
        "name": "test-mcp",
        "version": "1.0.0",
        "capabilities": {
            "tools": [
                {"name": "read_file", "description": "Read a file", "inputSchema": {"type": "object"}},
            ]
        }
    }

    with patch.object(hub, '_handshake', return_value=mock_server_info):
        server_id = await hub.connect("http://localhost:3000")
        assert server_id is not None


@pytest.mark.asyncio
async def test_hub_exposes_tools_to_registry():
    """Test that after connecting, tools appear in ToolRegistry."""
    from tools.registry import ToolRegistry
    registry = ToolRegistry()
    hub = MCPHub(tool_registry=registry)

    mock_server_info = {
        "name": "github-mcp",
        "capabilities": {"tools": [
            {"name": "create_issue", "description": "Create GitHub issue", "inputSchema": {"type": "object", "properties": {"title": {"type": "string"}}}},
        ]}
    }

    with patch.object(hub, '_handshake', return_value=mock_server_info):
        await hub.connect("http://localhost:3001", server_name="github-mcp")

    tool = registry.get("github-mcp.create_issue")
    assert tool is not None


@pytest.mark.asyncio
async def test_hub_auto_discovers_by_name():
    """Test that MCP Hub can auto-discover servers by name."""
    discover = MCPAutoDiscover()

    result = await discover.find("filesystem")
    # Should return known MCP server info or suggest install command
    assert result is not None
    assert "name" in result or "install" in result


@pytest.mark.asyncio
async def test_hub_disconnects_server():
    """Test that MCP Hub can disconnect from a server."""
    from tools.registry import ToolRegistry
    registry = ToolRegistry()
    hub = MCPHub(tool_registry=registry)

    mock_server_info = {
        "name": "test-mcp",
        "capabilities": {"tools": []}
    }

    with patch.object(hub, '_handshake', return_value=mock_server_info):
        server_id = await hub.connect("http://localhost:3000")

    # Disconnect
    result = await hub.disconnect(server_id)
    assert result is True


@pytest.mark.asyncio
async def test_hub_lists_servers():
    """Test that MCP Hub can list all connected servers."""
    hub = MCPHub()

    mock_server_info = {
        "name": "test-mcp",
        "capabilities": {"tools": []}
    }

    with patch.object(hub, '_handshake', return_value=mock_server_info):
        await hub.connect("http://localhost:3000")

    servers = hub.list_servers()
    assert len(servers) > 0


@pytest.mark.asyncio
async def test_auto_discover_exact_match():
    """Test exact match in known MCP servers."""
    discover = MCPAutoDiscover()

    result = await discover.find("github")
    assert result is not None
    assert result["name"] == "github"


@pytest.mark.asyncio
async def test_auto_discover_partial_match():
    """Test partial match in known MCP servers."""
    discover = MCPAutoDiscover()

    result = await discover.find("drive")
    assert result is not None
    assert "drive" in result["name"]


@pytest.mark.asyncio
async def test_auto_discover_unknown_server():
    """Test behavior with unknown server name."""
    discover = MCPAutoDiscover()

    result = await discover.find("nonexistent-server-xyz")
    # Should return None for unknown servers
    assert result is None


@pytest.mark.asyncio
async def test_hub_handshake_failure():
    """Test handling of handshake failure."""
    hub = MCPHub()

    with patch.object(hub, '_handshake', return_value=None):
        with pytest.raises(ConnectionError):
            await hub.connect("http://localhost:9999")


@pytest.mark.asyncio
async def test_hub_multiple_connections():
    """Test connecting to multiple MCP servers."""
    from tools.registry import ToolRegistry
    registry = ToolRegistry()
    hub = MCPHub(tool_registry=registry)

    mock_server_info = {
        "name": "test-mcp",
        "capabilities": {"tools": []}
    }

    with patch.object(hub, '_handshake', return_value=mock_server_info):
        server1 = await hub.connect("http://localhost:3000", server_name="server1")
        server2 = await hub.connect("http://localhost:3001", server_name="server2")

    assert server1 != server2
    assert len(hub.list_servers()) == 2

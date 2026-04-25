# tests/tools/test_registry.py
import pytest
from tools.registry import ToolRegistry
from tools.base_tool import BaseTool, ToolMeta, ToolResult


class MockTool(BaseTool):
    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="mock_tool",
            description="A mock tool for testing",
            parameters={"type": "object", "properties": {}},
            risk_score=0.1,
            categories=["test"],
        )

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, data="mock result", tool_name="mock_tool")


class SearchTool(BaseTool):
    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="search_tool",
            description="Search the web",
            parameters={},
            risk_score=0.3,
            categories=["web"],
        )

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, data="", tool_name="search_tool")


def test_registry_initialization():
    """Registry initializes empty."""
    reg = ToolRegistry()
    assert len(reg.list_tools()) == 0


def test_register_adds_tool():
    """Register adds tool to registry."""
    reg = ToolRegistry()
    tool = MockTool()

    reg.register(tool)

    tools = reg.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "mock_tool"


def test_unregister_removes_tool():
    """Unregister removes tool."""
    reg = ToolRegistry()
    tool = MockTool()

    reg.register(tool)
    reg.unregister("mock_tool")

    assert len(reg.list_tools()) == 0


def test_discover_finds_relevant_tools():
    """Discover returns relevant tools by semantic match."""
    reg = ToolRegistry()
    reg.register(MockTool())
    reg.register(SearchTool())

    results = reg.discover("I need to browse the internet")

    assert len(results) > 0
    # search_tool should rank higher for web queries
    assert any(r.name == "search_tool" for r in results)


def test_get_tool_by_name():
    """Get retrieves a tool by name."""
    reg = ToolRegistry()
    reg.register(MockTool())

    tool = reg.get("mock_tool")
    assert tool is not None
    assert tool.meta.name == "mock_tool"


def test_get_nonexistent_returns_none():
    """Get returns None for missing tools."""
    reg = ToolRegistry()

    tool = reg.get("does_not_exist")
    assert tool is None


@pytest.mark.asyncio
async def test_invoke_executes_tool():
    """Invoke executes a tool with parameters."""
    reg = ToolRegistry()
    reg.register(MockTool())

    result = await reg.invoke("mock_tool", {})

    assert result.success is True
    assert result.data == "mock result"

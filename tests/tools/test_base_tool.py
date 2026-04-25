import pytest
from abc import ABC
from tools.base_tool import BaseTool, ToolMeta, ToolResult


class MockTool(BaseTool):
    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="mock_tool",
            description="A mock tool for testing",
            parameters={"type": "object", "properties": {}},
            risk_score=0.1,
        )

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, data="mock result", tool_name="mock_tool")


def test_tool_meta_creation():
    """ToolMeta captures tool metadata."""
    meta = ToolMeta(
        name="test_tool",
        description="A test tool",
        parameters={"type": "object", "properties": {}},
        risk_score=0.1,
    )

    assert meta.name == "test_tool"
    assert meta.risk_score == 0.1


def test_tool_result_creation():
    """ToolResult captures execution results."""
    result = ToolResult(
        success=True,
        data="test output",
        tool_name="test_tool",
    )

    assert result.success is True
    assert result.data == "test output"


def test_base_tool_is_abstract():
    """BaseTool cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseTool()


def test_concrete_tool_implementation():
    """Concrete tool subclasses BaseTool."""
    tool = MockTool()
    assert tool.meta.name == "mock_tool"

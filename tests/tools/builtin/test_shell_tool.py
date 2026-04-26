# tests/tools/builtin/test_shell_tool.py
import pytest
from tools.builtin.shell_tool import ShellTool
from tools.base_tool import ToolResult


@pytest.mark.asyncio
async def test_shell_tool_executes_command():
    """Shell tool can execute simple commands."""
    tool = ShellTool()

    result = await tool.execute(command="echo hello")

    assert result.success is True
    assert "hello" in result.data


@pytest.mark.asyncio
async def test_shell_tool_captures_exit_code():
    """Shell tool captures exit codes."""
    tool = ShellTool()

    result = await tool.execute(command="exit 0")

    assert result.success is True
    assert result.metadata.get("exit_code") == 0


@pytest.mark.asyncio
async def test_shell_tool_handles_errors():
    """Shell tool handles command errors."""
    tool = ShellTool()

    result = await tool.execute(command="false")  # Always exits with 1

    assert result.success is False
    assert result.error != ""


def test_shell_tool_metadata():
    """Shell tool has correct metadata."""
    tool = ShellTool()

    assert tool.meta.name == "shell"
    assert "execute" in tool.meta.description.lower()
    assert tool.meta.risk_score > 0.5  # Shell commands are risky

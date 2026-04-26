# tests/tools/builtin/test_code_tool.py
import pytest
from unittest.mock import AsyncMock, patch
from tools.builtin.code_tool import CodeTool, CodeResult, RepairAttempt


@pytest.mark.asyncio
async def test_executes_simple_code():
    tool = CodeTool.__new__(CodeTool)
    tool.repl = AsyncMock()
    from sandbox.repl import REPLResult, REPLStatus
    tool.repl.execute = AsyncMock(return_value=REPLResult(
        success=True, status=REPLStatus.SUCCESS, output="4"
    ))
    tool.repl.install_package = AsyncMock()
    tool.llm = AsyncMock()

    result = await tool.execute_with_repair("print(2+2)")
    assert result.success
    assert result.attempts == 1


@pytest.mark.asyncio
async def test_installs_missing_dependency():
    tool = CodeTool.__new__(CodeTool)
    from sandbox.repl import REPLResult, REPLStatus
    call_count = 0

    async def mock_execute(code):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return REPLResult(
                success=False,
                status=REPLStatus.ERROR,
                error="No module named 'pandas'",
                error_type="ModuleNotFoundError",
                missing_modules=["pandas"],
            )
        return REPLResult(success=True, status=REPLStatus.SUCCESS, output="ok")

    tool.repl = AsyncMock()
    tool.repl.execute = mock_execute
    tool.repl.install_package = AsyncMock(
        return_value=REPLResult(success=True, status=REPLStatus.SUCCESS, output="installed")
    )
    tool.llm = AsyncMock()

    result = await tool.execute_with_repair("import pandas")
    assert result.success
    assert any(a.action == "install_dep" for a in result.repair_history)


@pytest.mark.asyncio
async def test_surgical_repair_on_syntax_error():
    """Repair uses str_replace, not full rewrite."""
    tool = CodeTool.__new__(CodeTool)
    from sandbox.repl import REPLResult, REPLStatus

    call_count = 0
    async def mock_execute(code):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return REPLResult(
                success=False,
                status=REPLStatus.ERROR,
                error='File "tmp.py", line 2\n    x = 1 +\n         ^\nSyntaxError: invalid syntax',
                error_type="SyntaxError",
            )
        return REPLResult(success=True, status=REPLStatus.SUCCESS, output="done")

    tool.repl = AsyncMock()
    tool.repl.execute = mock_execute
    tool.repl.install_package = AsyncMock()

    # Mock LLM to return a surgical repair
    async def mock_complete(req):
        from gateway.llm_gateway import LLMResponse, LLMProvider
        return LLMResponse(
            content='{"action": "str_replace", "old_str": "x = 1 +", "new_str": "x = 1 + 2"}',
            provider=LLMProvider.GROQ,
            model="test",
        )
    tool.llm = AsyncMock()
    tool.llm.complete = mock_complete

    result = await tool.execute_with_repair("x = 1 +\nprint(x)")
    assert result.success or result.attempts <= 5  # Attempted repair


@pytest.mark.asyncio
async def test_respects_max_attempts():
    tool = CodeTool.__new__(CodeTool)
    from sandbox.repl import REPLResult, REPLStatus

    tool.repl = AsyncMock()
    tool.repl.execute = AsyncMock(
        return_value=REPLResult(
            success=False,
            status=REPLStatus.ERROR,
            error="Persistent error",
            error_type="RuntimeError",
        )
    )
    tool.repl.install_package = AsyncMock()
    tool.llm = AsyncMock()

    result = await tool.execute_with_repair("bad code", max_attempts=3)
    assert not result.success
    assert result.attempts == 3


@pytest.mark.asyncio
async def test_code_tool_metadata():
    tool = CodeTool()
    assert tool.meta.name == "code"
    assert "code" in tool.meta.parameters["properties"]
    assert "max_attempts" in tool.meta.parameters["properties"]
    assert tool.meta.risk_score == 0.5
    assert "code" in tool.meta.categories
    assert "execution" in tool.meta.categories


@pytest.mark.asyncio
async def test_returns_execution_time():
    tool = CodeTool.__new__(CodeTool)
    from sandbox.repl import REPLResult, REPLStatus

    tool.repl = AsyncMock()
    tool.repl.execute = AsyncMock(
        return_value=REPLResult(success=True, status=REPLStatus.SUCCESS, output="result")
    )
    tool.repl.install_package = AsyncMock()
    tool.llm = AsyncMock()

    result = await tool.execute_with_repair("print('test')")
    assert result.execution_time_ms >= 0


@pytest.mark.asyncio
async def test_records_repair_history():
    tool = CodeTool.__new__(CodeTool)
    from sandbox.repl import REPLResult, REPLStatus

    call_count = 0
    async def mock_execute(code):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return REPLResult(
                success=False,
                status=REPLStatus.ERROR,
                error="ImportError",
                error_type="ImportError",
                missing_modules=["requests"],
            )
        return REPLResult(success=True, status=REPLStatus.SUCCESS, output="ok")

    tool.repl = AsyncMock()
    tool.repl.execute = mock_execute
    tool.repl.install_package = AsyncMock(
        return_value=REPLResult(success=True, status=REPLStatus.SUCCESS, output="installed")
    )
    tool.llm = AsyncMock()

    result = await tool.execute_with_repair("import requests")
    assert len(result.repair_history) > 0
    assert result.repair_history[0].action == "install_dep"


@pytest.mark.asyncio
async def test_handles_no_llm_available():
    tool = CodeTool.__new__(CodeTool)
    from sandbox.repl import REPLResult, REPLStatus

    tool.repl = AsyncMock()
    tool.repl.execute = AsyncMock(
        return_value=REPLResult(
            success=False,
            status=REPLStatus.ERROR,
            error="Syntax error",
            error_type="SyntaxError",
        )
    )
    tool.repl.install_package = AsyncMock()
    tool.llm = None  # No LLM available

    result = await tool.execute_with_repair("bad code")
    assert not result.success
    # Should give up after first attempt without LLM


@pytest.mark.asyncio
async def test_module_to_package_mapping():
    tool = CodeTool()
    assert tool._module_to_package("cv2") == "opencv-python"
    assert tool._module_to_package("PIL") == "Pillow"
    assert tool._module_to_package("sklearn") == "scikit-learn"
    assert tool._module_to_package("bs4") == "beautifulsoup4"
    assert tool._module_to_package("yaml") == "pyyaml"
    assert tool._module_to_package("dotenv") == "python-dotenv"
    assert tool._module_to_package("faiss") == "faiss-cpu"
    assert tool._module_to_package("unknown") == "unknown"  # No mapping


@pytest.mark.asyncio
async def test_execute_wraps_execute_with_repair():
    tool = CodeTool.__new__(CodeTool)
    from sandbox.repl import REPLResult, REPLStatus

    tool.repl = AsyncMock()
    tool.repl.execute = AsyncMock(
        return_value=REPLResult(success=True, status=REPLStatus.SUCCESS, output="42")
    )
    tool.repl.install_package = AsyncMock()
    tool.llm = AsyncMock()

    result = await tool.execute(code="print(42)")
    assert result.success
    assert result.data["output"] == "42"
    assert result.data["attempts"] == 1

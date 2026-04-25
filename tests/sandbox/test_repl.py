# tests/sandbox/test_repl.py
import pytest
import asyncio
from sandbox.repl import PythonREPL, REPLResult, REPLStatus
from sandbox.trust_zones import TrustZone, ExecutionContext


def test_execution_context_creation():
    """ExecutionContext captures trust and timeout info."""
    ctx = ExecutionContext(
        zone=TrustZone.SANDBOXED,
        timeout_seconds=30,
        allowed_imports=["os", "sys"],
    )

    assert ctx.zone == TrustZone.SANDBOXED
    assert ctx.timeout_seconds == 30


def test_trust_zone_levels_ordered():
    """Trust zones have proper ordering."""
    assert TrustZone.TRUSTED.value < TrustZone.SANDBOXED.value
    assert TrustZone.SANDBOXED.value < TrustZone.ISOLATED.value


@pytest.mark.asyncio
async def test_repl_executes_simple_code():
    """REPL can execute simple Python."""
    repl = PythonREPL()

    result = await repl.execute("x = 1 + 1")

    assert result.success is True
    assert result.output == ""


@pytest.mark.asyncio
async def test_repl_captures_output():
    """REPL captures print output."""
    repl = PythonREPL()

    result = await repl.execute("print('hello world')")

    assert result.success is True
    assert "hello world" in result.output


@pytest.mark.asyncio
async def test_repl_detects_module_not_found():
    """REPL identifies missing module errors."""
    repl = PythonREPL()

    result = await repl.execute("import nonexistent_module_xyz")

    assert result.success is False
    assert "ModuleNotFoundError" in result.error or "No module named" in result.error


@pytest.mark.asyncio
async def test_repl_respects_timeout():
    """REPL timeouts on infinite loops."""
    repl = PythonREPL(timeout=1)

    result = await repl.execute("while True: pass")

    assert result.success is False
    assert result.status == REPLStatus.TIMEOUT
    assert "timed" in result.error.lower()


@pytest.mark.asyncio
async def test_repl_preserves_state():
    """REPL maintains state between calls."""
    repl = PythonREPL()

    await repl.execute("x = 42")
    result = await repl.execute("print(x)")

    assert result.success is True
    assert "42" in result.output

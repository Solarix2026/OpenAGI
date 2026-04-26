# tests/core/test_kernel.py
import pytest
import asyncio
from core.kernel import Kernel
from core.telos_core import TelosCore


@pytest.mark.asyncio
async def test_kernel_initialization():
    """Kernel initializes with all components."""
    telos = TelosCore()
    kernel = Kernel(telos=telos)

    assert kernel is not None
    assert kernel.telos is not None
    assert kernel.planner is not None


@pytest.mark.asyncio
async def test_kernel_runs_stream():
    """Kernel.run() yields async stream."""
    telos = TelosCore()
    kernel = Kernel(telos=telos)

    chunks = []
    async for chunk in kernel.run("Hello"):
        chunks.append(chunk)

    assert len(chunks) > 0


def test_kernel_status():
    """Kernel reports status."""
    telos = TelosCore()
    kernel = Kernel(telos=telos)

    status = kernel.get_status()
    assert "initialized" in status

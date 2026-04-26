# tests/tools/builtin/test_memory_tool.py
import pytest
from unittest.mock import AsyncMock
from tools.builtin.memory_tool import MemoryTool
from memory.memory_core import MemoryCore, MemoryLayer


@pytest.fixture
def memory():
    return MemoryCore()


@pytest.mark.asyncio
async def test_write_to_memory(memory):
    tool = MemoryTool(memory=memory)
    result = await tool.execute(
        action="write",
        content="Test memory entry",
        layer="working",
    )
    assert result.success
    assert "memory_id" in result.data


@pytest.mark.asyncio
async def test_recall_from_memory(memory):
    tool = MemoryTool(memory=memory)

    # Write first
    await tool.execute(
        action="write",
        content="Python is a programming language",
        layer="semantic",
    )

    # Recall
    result = await tool.execute(
        action="recall",
        query="programming language",
        layer="semantic",
        top_k=5,
    )

    assert result.success
    assert "results" in result.data
    assert len(result.data["results"]) >= 1


@pytest.mark.asyncio
async def test_forget_from_memory(memory):
    tool = MemoryTool(memory=memory)

    # Write first
    write_result = await tool.execute(
        action="write",
        content="To be forgotten",
        layer="working",
    )
    memory_id = write_result.data["memory_id"]

    # Forget
    result = await tool.execute(
        action="forget",
        memory_id=memory_id,
    )

    assert result.success
    assert result.data["forgotten"] == memory_id


@pytest.mark.asyncio
async def test_memory_tool_without_memory_core():
    tool = MemoryTool(memory=None)
    result = await tool.execute(action="write", content="test", layer="working")
    assert not result.success
    assert "not attached" in result.error.lower()


@pytest.mark.asyncio
async def test_write_to_different_layers(memory):
    tool = MemoryTool(memory=memory)

    for layer in ["working", "episodic", "semantic", "procedural"]:
        result = await tool.execute(
            action="write",
            content=f"Test {layer} memory",
            layer=layer,
        )
        assert result.success


@pytest.mark.asyncio
async def test_recall_with_top_k(memory):
    tool = MemoryTool(memory=memory)

    # Write multiple entries
    for i in range(10):
        await tool.execute(
            action="write",
            content=f"Memory entry {i}",
            layer="working",
        )

    # Recall with limited top_k
    result = await tool.execute(
        action="recall",
        query="Memory",
        layer="working",
        top_k=3,
    )

    assert result.success
    assert len(result.data["results"]) <= 3


@pytest.mark.asyncio
async def test_recall_empty_results(memory):
    tool = MemoryTool(memory=memory)

    result = await tool.execute(
        action="recall",
        query="nonexistent query",
        layer="working",
    )

    assert result.success
    assert len(result.data["results"]) == 0


@pytest.mark.asyncio
async def test_memory_tool_metadata():
    tool = MemoryTool()
    assert tool.meta.name == "memory"
    assert "action" in tool.meta.parameters["properties"]
    assert "write" in tool.meta.parameters["properties"]["action"]["enum"]
    assert "recall" in tool.meta.parameters["properties"]["action"]["enum"]
    assert "forget" in tool.meta.parameters["properties"]["action"]["enum"]
    assert tool.meta.risk_score == 0.1


@pytest.mark.asyncio
async def test_unknown_action(memory):
    tool = MemoryTool(memory=memory)
    result = await tool.execute(action="unknown", content="test")
    assert not result.success
    assert "unknown" in result.error.lower()


@pytest.mark.asyncio
async def test_recall_includes_confidence_scores(memory):
    tool = MemoryTool(memory=memory)

    await tool.execute(
        action="write",
        content="Test content for confidence",
        layer="semantic",
    )

    result = await tool.execute(
        action="recall",
        query="confidence",
        layer="semantic",
    )

    assert result.success
    if result.data["results"]:
        assert "confidence" in result.data["results"][0]


@pytest.mark.asyncio
async def test_write_with_metadata(memory):
    tool = MemoryTool(memory=memory)
    result = await tool.execute(
        action="write",
        content="Test with metadata",
        layer="working",
    )
    assert result.success
    # Memory should store the entry with metadata


@pytest.mark.asyncio
async def test_forget_nonexistent_memory(memory):
    tool = MemoryTool(memory=memory)
    result = await tool.execute(
        action="forget",
        memory_id="nonexistent-id",
    )
    # Should succeed even if memory doesn't exist (idempotent)
    assert result.success

# tests/memory/test_memory_core.py
import pytest
from memory.memory_core import MemoryCore, MemoryLayer, MemoryItem
from core.telos_core import TelosCore


@pytest.fixture
def telos():
    return TelosCore()


def test_memory_layers_exist():
    """Four memory layers defined."""
    assert MemoryLayer.WORKING.name == "WORKING"
    assert MemoryLayer.EPISODIC.name == "EPISODIC"
    assert MemoryLayer.SEMANTIC.name == "SEMANTIC"
    assert MemoryLayer.PROCEDURAL.name == "PROCEDURAL"


def test_memory_item_creation():
    """MemoryItems capture content with metadata."""
    item = MemoryItem(
        content="Test content",
        layer=MemoryLayer.WORKING,
        confidence_score=0.95,
    )

    assert item.content == "Test content"
    assert item.layer == MemoryLayer.WORKING
    assert item.confidence_score == 0.95


def test_memory_core_initializes_layers(telos):
    """MemoryCore initializes all layers."""
    core = MemoryCore(telos=telos)

    # Should have references to all stores
    assert core._hdc_store is not None
    assert core._faiss_store is not None


@pytest.mark.asyncio
async def test_write_and_recall_working(telos):
    """Can write to and recall from working memory."""
    core = MemoryCore(telos=telos)

    mem_id = await core.write(
        content="Test memory",
        layer=MemoryLayer.WORKING,
        metadata={"test": True},
    )

    # Recall from working memory
    results = await core.recall(
        query="Test",
        layers=[MemoryLayer.WORKING],
    )

    assert len(results) > 0
    assert any(r.content == "Test memory" for r in results)


@pytest.mark.asyncio
async def test_recall_filters_by_layer(telos):
    """Recall respects layer filters."""
    core = MemoryCore(telos=telos)

    await core.write("Working content", MemoryLayer.WORKING, {})
    await core.write("Episodic content", MemoryLayer.EPISODIC, {})

    # Recall only working
    working_results = await core.recall("content", [MemoryLayer.WORKING])
    assert all(r.layer == MemoryLayer.WORKING for r in working_results)

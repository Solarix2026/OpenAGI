# tests/memory/test_hdc_active.py
"""Tests for HDC Active Memory - session-scoped hypervector working memory."""
import pytest
import numpy as np
from memory.hdc_active_memory import HDCActiveMemory


@pytest.mark.asyncio
async def test_hdc_active_stores_and_recalls():
    """Test that HDC Active Memory can store and recall content."""
    mem = HDCActiveMemory(dim=1000)
    await mem.store("session-1", "User wants to build a REST API")
    results = await mem.recall("REST API development", session_id="session-1")
    assert len(results) > 0
    assert any("REST" in r["content"] for r in results)


@pytest.mark.asyncio
async def test_hdc_active_binding():
    """Test that HDC correctly binds event + context."""
    mem = HDCActiveMemory(dim=1000)
    await mem.store("s1", "plan_created", event_type="PLAN")
    await mem.store("s1", "tool_called:web_search", event_type="TOOL_CALL")
    results = await mem.recall("tool usage", session_id="s1")
    assert len(results) > 0


@pytest.mark.asyncio
async def test_hdc_active_session_isolation():
    """Test that different sessions don't bleed into each other."""
    mem = HDCActiveMemory(dim=1000)
    await mem.store("session-A", "Project A secret")
    await mem.store("session-B", "Project B secret")
    results_a = await mem.recall("secret", session_id="session-A")
    assert all("A" in r.get("content", "") for r in results_a)


@pytest.mark.asyncio
async def test_hdc_active_forget_session():
    """Test that forgetting a session clears all its memories."""
    mem = HDCActiveMemory(dim=1000)
    await mem.store("s-temp", "Temporary context")
    await mem.forget_session("s-temp")
    results = await mem.recall("Temporary", session_id="s-temp")
    assert len(results) == 0


@pytest.mark.asyncio
async def test_hdc_active_lru_eviction():
    """Test that LRU eviction works when capacity is exceeded."""
    mem = HDCActiveMemory(dim=1000)
    # Store more than MAX_ITEMS_PER_SESSION (200)
    for i in range(250):
        await mem.store("s-lru", f"Item {i}", event_type="TEST")

    # Should have evicted oldest items
    stats = mem.get_session_stats("s-lru")
    assert stats["total_items"] <= 200


@pytest.mark.asyncio
async def test_hdc_active_event_type_filter():
    """Test that event type filtering works."""
    mem = HDCActiveMemory(dim=1000)
    await mem.store("s1", "Plan created", event_type="PLAN")
    await mem.store("s1", "Tool called", event_type="TOOL_CALL")
    await mem.store("s1", "Error occurred", event_type="ERROR")

    results = await mem.recall("test", session_id="s1", event_type_filter="PLAN")
    assert all(r["event_type"] == "PLAN" for r in results)


@pytest.mark.asyncio
async def test_hdc_active_metadata_storage():
    """Test that metadata is stored and retrieved correctly."""
    mem = HDCActiveMemory(dim=1000)
    metadata = {"priority": "high", "tags": ["important"]}
    await mem.store("s1", "Important task", metadata=metadata)

    results = await mem.recall("task", session_id="s1")
    assert len(results) > 0


@pytest.mark.asyncio
async def test_hdc_active_empty_session():
    """Test behavior with empty sessions."""
    mem = HDCActiveMemory(dim=1000)
    results = await mem.recall("anything", session_id="nonexistent")
    assert len(results) == 0


@pytest.mark.asyncio
async def test_hdc_active_multiple_sessions():
    """Test handling multiple concurrent sessions."""
    mem = HDCActiveMemory(dim=1000)
    sessions = ["s1", "s2", "s3"]

    for session in sessions:
        await mem.store(session, f"Content for {session}")

    # Each session should have its own content
    for session in sessions:
        results = await mem.recall("content", session_id=session)
        assert len(results) > 0
        assert session in results[0]["content"]


@pytest.mark.asyncio
async def test_hdc_active_session_stats():
    """Test that session statistics are accurate."""
    mem = HDCActiveMemory(dim=1000)
    await mem.store("s1", "Item 1", event_type="PLAN")
    await mem.store("s1", "Item 2", event_type="TOOL_CALL")
    await mem.store("s1", "Item 3", event_type="PLAN")

    stats = mem.get_session_stats("s1")
    assert stats["total_items"] == 3
    assert stats["by_event_type"]["PLAN"] == 2
    assert stats["by_event_type"]["TOOL_CALL"] == 1

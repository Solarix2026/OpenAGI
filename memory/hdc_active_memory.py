# memory/hdc_active_memory.py
"""HDC Active Working Memory.

High-speed in-session memory using Hyperdimensional Computing.
Used for:
- Current task context (what step are we on?)
- Recent tool calls (what did we just do?)
- Session state (what does the user know right now?)

Key properties:
- Sub-millisecond lookup (pure numpy, no DB)
- Associative recall (fuzzy matching via Hamming distance)
- Session-isolated (different sessions don't bleed)
- Auto-eviction (LRU when capacity exceeded)
"""
from __future__ import annotations

import asyncio
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import numpy as np
import structlog

from memory.hdc_store import HDCStore

logger = structlog.get_logger()

MAX_ITEMS_PER_SESSION = 200
DEFAULT_DIM = 10000


@dataclass
class ActiveMemoryItem:
    """An item in active memory."""
    memory_id: str
    content: str
    session_id: str
    event_type: str
    timestamp: datetime
    hypervector: Optional[np.ndarray] = None


class HDCActiveMemory:
    """
    Fast session-scoped working memory via HDC hypervectors.

    Uses XOR binding to associate:
    - Session context vector (unique per session)
    - Event type vector (PLAN, TOOL_CALL, ERROR, USER_INPUT, etc.)
    - Content vector (actual text)

    Recall: query vector vs stored bundles → Hamming similarity → top-k
    """

    def __init__(self, dim: int = DEFAULT_DIM) -> None:
        self.dim = dim
        self._hdc = HDCStore(dim=dim)

        # Per-session item tracking (LRU)
        self._session_items: dict[str, OrderedDict[str, ActiveMemoryItem]] = {}
        self._session_vectors: dict[str, np.ndarray] = {}

        # Event type vectors (pre-generated, deterministic)
        self._event_vectors = self._init_event_vectors()

        logger.info("hdc_active_memory.initialized", dim=dim)

    def _init_event_vectors(self) -> dict[str, np.ndarray]:
        """Pre-generate deterministic hypervectors for known event types."""
        event_types = [
            "PLAN", "TOOL_CALL", "TOOL_RESULT", "ERROR",
            "USER_INPUT", "AGENT_RESPONSE", "MEMORY_READ",
            "MEMORY_WRITE", "GOAL_START", "GOAL_COMPLETE",
        ]
        return {
            et: self._hdc.encode(f"__event__{et.lower()}")
            for et in event_types
        }

    def _get_session_vector(self, session_id: str) -> np.ndarray:
        """Get or create a unique vector for this session."""
        if session_id not in self._session_vectors:
            self._session_vectors[session_id] = self._hdc.encode(
                f"__session__{session_id}"
            )
        return self._session_vectors[session_id]

    async def store(
        self,
        session_id: str,
        content: str,
        event_type: str = "USER_INPUT",
        metadata: dict[str, Any] = None,
    ) -> str:
        """Store content bound to session + event type."""
        import uuid
        memory_id = f"{session_id}_{uuid.uuid4().hex[:8]}"

        # Build composite hypervector: bind session × event × content
        session_hv = self._get_session_vector(session_id)
        event_hv = self._event_vectors.get(
            event_type, self._hdc.encode(f"__event__{event_type.lower()}")
        )
        content_hv = self._hdc.encode(content)

        # XOR bind all three (associative — can be retrieved via any component)
        composite = self._hdc.bind(
            self._hdc.bind(session_hv, event_hv),
            content_hv
        )

        # Store in HDC
        self._hdc.memories[memory_id] = composite
        self._hdc.metadata[memory_id] = {
            "content": content,
            "session_id": session_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            **(metadata or {}),
        }

        # Track per-session (LRU eviction)
        if session_id not in self._session_items:
            self._session_items[session_id] = OrderedDict()

        self._session_items[session_id][memory_id] = ActiveMemoryItem(
            memory_id=memory_id,
            content=content,
            session_id=session_id,
            event_type=event_type,
            timestamp=datetime.utcnow(),
            hypervector=composite,
        )

        # Evict if over capacity
        while len(self._session_items[session_id]) > MAX_ITEMS_PER_SESSION:
            oldest_id, _ = self._session_items[session_id].popitem(last=False)
            self._hdc.delete(oldest_id)

        return memory_id

    async def recall(
        self,
        query: str,
        session_id: str,
        event_type_filter: Optional[str] = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Recall from active memory for a session."""
        if session_id not in self._session_items or not self._session_items[session_id]:
            return []

        # Build query vector bound to session
        session_hv = self._get_session_vector(session_id)
        query_hv = self._hdc.encode(query)
        query_composite = self._hdc.bind(session_hv, query_hv)

        # Search only within this session's items
        session_memories = {
            mid: self._hdc.memories[mid]
            for mid in self._session_items[session_id]
            if mid in self._hdc.memories
        }

        # Compute similarities
        scores = []
        for memory_id, hv in session_memories.items():
            sim = self._hdc.similarity(query_composite, hv)
            meta = self._hdc.metadata.get(memory_id, {})

            if event_type_filter and meta.get("event_type") != event_type_filter:
                continue

            scores.append((sim, memory_id, meta))

        # Sort by similarity
        scores.sort(key=lambda x: -x[0])

        return [
            {"content": meta["content"], "event_type": meta.get("event_type"), "score": sim}
            for sim, _, meta in scores[:top_k]
        ]

    async def forget_session(self, session_id: str) -> int:
        """Clear all active memories for a session."""
        if session_id not in self._session_items:
            return 0

        cleared = 0
        for memory_id in list(self._session_items[session_id].keys()):
            self._hdc.delete(memory_id)
            cleared += 1

        del self._session_items[session_id]
        if session_id in self._session_vectors:
            del self._session_vectors[session_id]

        logger.info("hdc_active.session_cleared", session_id=session_id, count=cleared)
        return cleared

    def get_session_stats(self, session_id: str) -> dict:
        """Get statistics for a session."""
        items = self._session_items.get(session_id, {})
        event_counts: dict[str, int] = {}
        for item in items.values():
            event_counts[item.event_type] = event_counts.get(item.event_type, 0) + 1
        return {"total_items": len(items), "by_event_type": event_counts}

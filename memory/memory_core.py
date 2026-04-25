# memory/memory_core.py
"""Stratified memory: WORKING / EPISODIC / SEMANTIC / PROCEDURAL.

Four layers, each with distinct write/read/forget semantics:
- WORKING: In-process dict, wiped per session
- EPISODIC: HDC hypervectors, event-indexed
- SEMANTIC: FAISS dense vectors, topic-indexed
- PROCEDURAL: SQLite, how-to knowledge
"""
import asyncio
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import structlog

from config.settings import get_settings
from core.telos_core import TelosCore
from memory.faiss_store import FaissStore
from memory.hdc_store import HDCStore

logger = structlog.get_logger()


class MemoryLayer(Enum):
    """Four memory layers."""
    WORKING = auto()
    EPISODIC = auto()
    SEMANTIC = auto()
    PROCEDURAL = auto()


@dataclass(frozen=True)
class MemoryItem:
    """A single memory item."""
    memory_id: str = field(default_factory=lambda: str(uuid4()))
    content: str = ""
    layer: MemoryLayer = MemoryLayer.WORKING
    timestamp: datetime = field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None
    confidence_score: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    vector_hash: Optional[str] = None


class MemoryCore:
    """
    Stratified memory system with four layers.

    Each layer has different semantics for write, read, and forget:
    - Working: Fast in-process access, auto-expire
    - Episodic: HDC associative recall, event-based
    - Semantic: FAISS similarity, topic-based
    - Procedural: SQLite with JSON, how-to knowledge
    """

    def __init__(self, telos: Optional[TelosCore] = None):
        self.config = get_settings()
        self.telos = telos

        # Initialize stores
        self._working: dict[str, MemoryItem] = {}
        self._hdc_store = HDCStore(dim=self.config.memory.hdc_dim)
        self._faiss_store = FaissStore(dim=self.config.memory.semantic_dim)
        self._procedural_db_path = self.config.memory.procedural_db_path

        # Ensure directories exist
        self._procedural_db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize procedural store
        self._init_procedural_db()

        logger.info(
            "memory.core.initialized",
            hdc_dim=self.config.memory.hdc_dim,
            semantic_dim=self.config.memory.semantic_dim,
        )

    def _init_procedural_db(self) -> None:
        """Initialize SQLite for procedural memory."""
        with sqlite3.connect(self._procedural_db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS procedural_memory (
                    memory_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    session_id TEXT,
                    confidence_score REAL,
                    category TEXT,
                    data JSON,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_proc_category
                ON procedural_memory(category)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_proc_session
                ON procedural_memory(session_id)
            """)

    async def write(
        self,
        content: str,
        layer: MemoryLayer,
        metadata: dict[str, Any],
        session_id: str = "unknown",
    ) -> str:
        """
        Write content to the specified memory layer.

        Returns memory_id for later retrieval.
        """
        # Check telos alignment for memories
        if self.telos:
            drift = self.telos.drift_score(content)
            if drift >= 0.7:
                logger.warning(
                    "memory.write.drift_detected",
                    drift=drift,
                    layer=layer.name,
                )

        memory_id = str(uuid4())
        item = MemoryItem(
            memory_id=memory_id,
            content=content,
            layer=layer,
            session_id=session_id,
            metadata=metadata,
        )

        if layer == MemoryLayer.WORKING:
            self._working[memory_id] = item
            logger.debug("memory.working.written", memory_id=memory_id)

        elif layer == MemoryLayer.EPISODIC:
            self._hdc_store.add(
                memory_id,
                content,
                {
                    **metadata,
                    "layer": "episodic",
                    "session_id": session_id,
                },
            )
            logger.debug("memory.episodic.written", memory_id=memory_id)

        elif layer == MemoryLayer.SEMANTIC:
            self._faiss_store.add(
                memory_id,
                content,
                {
                    **metadata,
                    "layer": "semantic",
                    "session_id": session_id,
                },
            )
            logger.debug("memory.semantic.written", memory_id=memory_id)

        elif layer == MemoryLayer.PROCEDURAL:
            self._write_procedural(item)
            logger.debug("memory.procedural.written", memory_id=memory_id)

        return memory_id

    def _write_procedural(self, item: MemoryItem) -> None:
        """Write to procedural SQLite store."""
        category = item.metadata.get("category", "general")

        with sqlite3.connect(self._procedural_db_path) as conn:
            conn.execute(
                """
                INSERT INTO procedural_memory
                (memory_id, content, timestamp, session_id, confidence_score, category, data, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.memory_id,
                    item.content,
                    item.timestamp.isoformat(),
                    item.session_id,
                    item.confidence_score,
                    category,
                    json.dumps(item.metadata),
                    datetime.utcnow().isoformat(),
                ),
            )

    async def recall(
        self,
        query: str,
        layers: list[MemoryLayer],
        top_k: int = 5,
        session_id: Optional[str] = None,
    ) -> list[MemoryItem]:
        """
        Recall memories from specified layers.

        Returns sorted list of MemoryItem by relevance.
        """
        results: list[tuple[MemoryItem, float]] = []

        for layer in layers:
            if layer == MemoryLayer.WORKING:
                # Simple substring match for working memory
                matching = [
                    (item, 1.0 if query.lower() in item.content.lower() else 0.0)
                    for item in self._working.values()
                    if query.lower() in item.content.lower()
                ]
                results.extend(matching)

            elif layer == MemoryLayer.EPISODIC:
                # HDC semantic similarity
                hdc_results = self._hdc_store.query(query, top_k=top_k)
                for memory_id, score, meta in hdc_results:
                    item = MemoryItem(
                        memory_id=memory_id,
                        content=meta.get("content", ""),
                        layer=MemoryLayer.EPISODIC,
                        metadata=meta,
                    )
                    results.append((item, score))

            elif layer == MemoryLayer.SEMANTIC:
                # FAISS dense similarity
                faiss_results = self._faiss_store.query(query, top_k=top_k)
                for memory_id, score, meta in faiss_results:
                    item = MemoryItem(
                        memory_id=memory_id,
                        content=meta.get("content", ""),
                        layer=MemoryLayer.SEMANTIC,
                        metadata=meta,
                    )
                    results.append((item, score))

            elif layer == MemoryLayer.PROCEDURAL:
                # SQLite text search
                proc_results = self._query_procedural(query, session_id, top_k)
                results.extend(proc_results)

        # Sort by score descending
        results.sort(key=lambda x: -x[1])

        # Return just the items
        return [item for item, _ in results[:top_k]]

    def _query_procedural(
        self,
        query: str,
        session_id: Optional[str],
        top_k: int,
    ) -> list[tuple[MemoryItem, float]]:
        """Query procedural memory via SQLite."""
        with sqlite3.connect(self._procedural_db_path) as conn:
            if session_id:
                cursor = conn.execute(
                    """
                    SELECT memory_id, content, timestamp, session_id, confidence_score, data
                    FROM procedural_memory
                    WHERE (content LIKE ? OR category LIKE ?) AND session_id = ?
                    ORDER BY last_accessed DESC
                    LIMIT ?
                    """,
                    (f"%{query}%", f"%{query}%", session_id, top_k),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT memory_id, content, timestamp, session_id, confidence_score, data
                    FROM procedural_memory
                    WHERE content LIKE ? OR category LIKE ?
                    ORDER BY last_accessed DESC
                    LIMIT ?
                    """,
                    (f"%{query}%", f"%{query}%", top_k),
                )

            results = []
            for row in cursor:
                memory_id, content, timestamp, sid, conf, data = row
                metadata = json.loads(data) if data else {}
                item = MemoryItem(
                    memory_id=memory_id,
                    content=content,
                    layer=MemoryLayer.PROCEDURAL,
                    metadata=metadata,
                )
                # Score by recency
                results.append((item, conf or 0.5))

            return results

    async def consolidate(self) -> int:
        """
        Compress episodic → semantic.

        Find similar episodic memories and merge into semantic.
        Returns number of memories consolidated.
        """
        # Simple consolidation: similar memories get bundled
        consolidated = 0

        # Get all episodic memories
        for memory_id in list(self._hdc_store.memories.keys()):
            meta = self._hdc_store.metadata.get(memory_id)
            if not meta:
                continue

            content = meta.get("content", "")

            # Check for similar semantic memories
            similar = self._faiss_store.query(content, top_k=1, min_score=0.8)

            if similar:
                # Merge into existing semantic memory
                _, _, existing_meta = similar[0]
                existing_content = existing_meta.get("content", "")
                merged = f"{existing_content}\n---\n{content}"

                # Update the semantic memory (delete + re-add)
                self._faiss_store.delete(existing_meta["memory_id"])
                self._faiss_store.add(
                    existing_meta["memory_id"],
                    merged,
                    {**existing_meta, "consolidated": True},
                )

                # Remove episodic
                self._hdc_store.delete(memory_id)
                consolidated += 1
            else:
                # Move to semantic
                self._faiss_store.add(
                    memory_id,
                    content,
                    {**meta, "migrated": True},
                )
                self._hdc_store.delete(memory_id)
                consolidated += 1

        logger.info("memory.consolidated", count=consolidated)
        return consolidated

    async def forget(self, memory_id: str, reason: str) -> bool:
        """
        Forget a specific memory by ID.

        Logs the reason for forgetting.
        """
        # Try each store
        if memory_id in self._working:
            del self._working[memory_id]
            logger.info("memory.forgotten.working", memory_id=memory_id, reason=reason)
            return True

        if self._hdc_store.delete(memory_id):
            logger.info("memory.forgotten.episodic", memory_id=memory_id, reason=reason)
            return True

        if self._faiss_store.delete(memory_id):
            logger.info("memory.forgotten.semantic", memory_id=memory_id, reason=reason)
            return True

        # Check procedural
        with sqlite3.connect(self._procedural_db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM procedural_memory WHERE memory_id = ?",
                (memory_id,),
            )
            if cursor.rowcount > 0:
                logger.info("memory.forgotten.procedural", memory_id=memory_id, reason=reason)
                return True

        return False

    async def clear_working(self) -> None:
        """Clear working memory (called on new session)."""
        cleared = len(self._working)
        self._working.clear()
        logger.info("memory.working.cleared", count=cleared)

    def get_stats(self) -> dict[str, int]:
        """Get memory statistics."""
        with sqlite3.connect(self._procedural_db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM procedural_memory")
            procedural_count = cursor.fetchone()[0]

        return {
            "working": len(self._working),
            "episodic": len(self._hdc_store.memories),
            "semantic": len(self._faiss_store.ids),
            "procedural": procedural_count,
        }

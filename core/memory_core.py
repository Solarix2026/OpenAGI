# Copyright (c) 2026 HackerTMJ (门牌号3号)
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/HackerTMJ/OpenAGI

"""
memory_core.py — 4-tier memory system v2.0 (Background FAISS)

Tier 1 — Episodic : raw events (SQLite) → what happened
Tier 2 — Semantic : knowledge embeddings (FAISS) → what is known
Tier 3 — Procedural: tool outcomes + patterns → what works
Tier 4 — Meta : self-knowledge, state → what I am

Performance: FAISS rebuilds happen in background thread, non-blocking.
"""
import os, json, sqlite3, logging, threading, time
from pathlib import Path
from datetime import datetime
from typing import Optional

log = logging.getLogger("Memory")

# Global model cache — load ONCE, reuse forever
_EMBEDDING_MODEL = None

def _get_embedding_model():
    """Get cached SentenceTransformer model (loads only once)."""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            _EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
            log.info("Embedding model loaded (cached)")
        except Exception as e:
            log.warning(f"Could not load embedding model: {e}")
    return _EMBEDDING_MODEL


class AgentMemory:
    def __init__(self, workspace: str = "./workspace"):
        self.ws = Path(workspace)
        self.ws.mkdir(parents=True, exist_ok=True)
        self.db_path = str(self.ws / "agent_state.db")
        self._lock = threading.Lock()
        self._conn = self._connect()
        self._init_schema()
        self._faiss_index = None  # lazy init
        self._faiss_texts = []
        self._faiss_dirty = True
        # Background rebuild support
        self._rebuild_lock = threading.Lock()
        self._rebuilding = False
        log.info(f"Memory initialized at {self.db_path}")

    def _connect(self):
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=5.0,
            isolation_level=None  # Autocommit mode for less locking
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA temp_store=MEMORY")
        return conn

    def __del__(self):
        """Ensure database connection is closed on destruction."""
        if hasattr(self, '_conn') and self._conn:
            try:
                self._conn.close()
            except Exception:
                pass

    def _init_schema(self):
        with self._lock:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS episodic (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT DEFAULT (datetime('now')),
                    event_type TEXT,
                    content TEXT,
                    context TEXT,
                    importance REAL DEFAULT 0.5
                );
                CREATE TABLE IF NOT EXISTS procedural (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT DEFAULT (datetime('now')),
                    tool TEXT,
                    outcome TEXT,
                    params TEXT,
                    success INTEGER,
                    duration_ms INTEGER
                );
                CREATE TABLE IF NOT EXISTS meta_knowledge (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    ts TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_ep_type ON episodic(event_type);
                CREATE INDEX IF NOT EXISTS idx_ep_ts ON episodic(ts);
                CREATE INDEX IF NOT EXISTS idx_proc_tool ON procedural(tool);
            """)
            self._conn.commit()

    # ── Episodic ─────────────────────────────────────────────────

    def log_event(self, event_type: str, content: str, context: dict = None, importance: float = 0.5):
        with self._lock:
            self._conn.execute(
                "INSERT INTO episodic(event_type, content, context, importance) VALUES (?,?,?,?)",
                (event_type, content[:2000], json.dumps(context or {}), importance)
            )
            self._conn.commit()
            self._faiss_dirty = True
        # Schedule background rebuild (non-blocking)
        self._schedule_faiss_rebuild()

    def search_events(self, query: str, limit: int = 5, event_type: str = None) -> list:
        """Hybrid search: vector similarity + SQL keyword fallback."""
        results = []
        # Vector search (if FAISS available and not rebuilding)
        try:
            results = self._vector_search(query, limit)
        except Exception:
            pass
        # SQL keyword fallback or supplement
        if len(results) < limit:
            sql_results = self._sql_search(query, limit, event_type)
            seen = {r.get("content") for r in results}
            for r in sql_results:
                if r.get("content") not in seen:
                    results.append(r)
        return results[:limit]

    def get_relevant_memory_context(self, query: str, threshold: float = 0.4) -> str:
        """SMART memory injection: only high-relevance memories, compressed."""
        if not query or len(query.strip()) < 3:
            return ""
        # Try vector search first
        relevant = []
        try:
            results = self._vector_search(query, limit=5)
            # Filter by importance and relevance
            relevant = [r for r in results if r.get("importance", 0.5) > threshold]
        except Exception:
            pass
        # Fallback: recent 2 events if no vector results
        if not relevant:
            recent = self.get_recent_timeline(limit=2)
            relevant = [r for r in recent if r.get("event_type") == "user_message"]
        if not relevant:
            return ""
        # Compress: max 100 chars per snippet
        snippets = [r.get("content", "")[:100] for r in relevant[:3]]
        return "Context: " + " | ".join(s for s in snippets if s)

    def _sql_search(self, query: str, limit: int, event_type: str = None) -> list:
        words = [w for w in query.lower().split() if len(w) > 2]
        if not words:
            with self._lock:
                rows = self._conn.execute(
                    "SELECT * FROM episodic ORDER BY ts DESC LIMIT ?",
                    (limit,)
                ).fetchall()
        else:
            conditions = " OR ".join(f"lower(content) LIKE '%{w}%'" for w in words[:5])
            type_filter = f"AND event_type = '{event_type}'" if event_type else ""
            with self._lock:
                rows = self._conn.execute(
                    f"SELECT * FROM episodic WHERE ({conditions}) {type_filter} ORDER BY importance DESC, ts DESC LIMIT ?",
                    (limit,)
                ).fetchall()
        return [dict(r) for r in rows]

    def _vector_search(self, query: str, limit: int) -> list:
        """FAISS semantic search over episodic content."""
        import numpy as np
        try:
            import faiss
        except ImportError:
            return []
        # If dirty and not rebuilding, trigger rebuild (but don't block)
        if self._faiss_dirty and not self._rebuilding:
            self._schedule_faiss_rebuild()
        # If rebuilding, fallback to SQL (don't block)
        if self._rebuilding or self._faiss_index is None or not self._faiss_texts:
            return []
        model = _get_embedding_model()
        if model is None:
            return []
        try:
            q_vec = model.encode([query], convert_to_numpy=True).astype("float32")
            faiss.normalize_L2(q_vec)
            D, I = self._faiss_index.search(q_vec, min(limit, len(self._faiss_texts)))
            return [self._faiss_texts[i] for i in I[0] if i < len(self._faiss_texts)]
        except Exception as e:
            log.debug(f"Vector search failed: {e}")
            return []

    def _schedule_faiss_rebuild(self):
        """Non-blocking: rebuild FAISS in background thread."""
        if self._rebuilding:
            return
        def _do_rebuild():
            with self._rebuild_lock:
                self._rebuilding = True
            try:
                self._rebuild_faiss_sync()
            finally:
                self._rebuilding = False
        threading.Thread(target=_do_rebuild, daemon=True, name="FAISSRebuild").start()

    def _rebuild_faiss_sync(self):
        """Synchronous FAISS rebuild (runs in background thread)."""
        try:
            import faiss
            import numpy as np
            model = _get_embedding_model()
            if model is None:
                return
            with self._lock:
                rows = self._conn.execute("SELECT * FROM episodic ORDER BY ts DESC LIMIT 500").fetchall()
            if not rows:
                return
            texts = [dict(r) for r in rows]
            vecs = model.encode([r["content"][:256] for r in texts], convert_to_numpy=True).astype("float32")
            faiss.normalize_L2(vecs)
            index = faiss.IndexFlatIP(vecs.shape[1])
            index.add(vecs)
            self._faiss_index = index
            self._faiss_texts = texts
            self._faiss_dirty = False
            log.info(f"FAISS index rebuilt with {len(texts)} entries")
        except Exception as e:
            log.debug(f"FAISS rebuild failed: {e}")

    # ── Procedural ───────────────────────────────────────────────

    def log_tool_outcome(self, tool: str, params: dict, outcome: str, success: bool, duration_ms: int = 0):
        with self._lock:
            self._conn.execute(
                "INSERT INTO procedural(tool,outcome,params,success,duration_ms) VALUES (?,?,?,?,?)",
                (tool, outcome[:500], json.dumps(params), int(success), duration_ms)
            )
            self._conn.commit()

    def get_tool_success_rate(self, tool: str) -> float:
        with self._lock:
            row = self._conn.execute("SELECT AVG(success) FROM procedural WHERE tool=?", (tool,)).fetchone()
            return float(row[0] or 0.5)

    # ── Meta knowledge ───────────────────────────────────────────

    def update_meta_knowledge(self, key: str, value):
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO meta_knowledge(key,value,ts) VALUES (?,?,datetime('now'))",
                (key, json.dumps(value))
            )
            self._conn.commit()

    def get_meta_knowledge(self, key: str):
        with self._lock:
            row = self._conn.execute("SELECT value FROM meta_knowledge WHERE key=?", (key,)).fetchone()
            if row:
                try:
                    return {"content": json.loads(row[0])}
                except Exception:
                    return {"content": row[0]}
            return {}

    def get_recent_timeline(self, limit: int = 20) -> list:
        with self._lock:
            rows = self._conn.execute(
                "SELECT ts, event_type, content FROM episodic ORDER BY ts DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def close(self):
        self._conn.close()


    # ── Memory Compression ────────────────────────────────────────

    def compress_episodic_to_semantic(self, since_hours=24) -> dict:
        """
        Called by CHRONOS_REVERIE nightly.
        Compress recent episodic events into semantic summary nodes.
        Reduces FAISS index: 500 episodic → ~50 semantic entries.
        """
        from datetime import datetime, timedelta
        cutoff = (datetime.now() - timedelta(hours=since_hours)).isoformat()

        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM episodic WHERE ts > ? ORDER BY ts DESC LIMIT 200",
                (cutoff,)
            ).fetchall()

        if len(rows) < 5:
            return {"compressed": 0, "reason": "not enough events"}

        events = [dict(r) for r in rows]
        events_text = "\n".join(
            f"[{e['event_type']}] {e['content'][:80]}"
            for e in events[:50]
        )

        # Use NVIDIA to compress
        try:
            from core.llm_gateway import call_nvidia
            import json
            import re

            prompt = f"""Compress these agent events into 5-8 key knowledge nodes.
Each node = one important fact/pattern worth remembering long-term.
Discard: noise, duplicates, transient "how are you" exchanges.
Keep: recurring patterns, capability usages, important user info.

Events: {events_text}

Return JSON: {{"nodes": [{{"summary": "...", "topic": "...", "importance": 0.0-1.0}}]}}"""

            raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=500, fast=True)
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if not m:
                return {"compressed": 0, "reason": "parse failed"}

            nodes = json.loads(m.group(0)).get("nodes", [])

            # Store semantic nodes
            with self._lock:
                for node in nodes:
                    self._conn.execute(
                        "INSERT INTO semantic_memory(summary,topic,importance,source_event_count,span_hours) VALUES(?,?,?,?,?)",
                        (
                            node["summary"][:500],
                            node.get("topic", ""),
                            node.get("importance", 0.5),
                            len(events),
                            since_hours
                        )
                    )
                self._conn.commit()

            log.info(f"[MEMORY] Compressed {len(events)} events → {len(nodes)} semantic nodes")
            return {"compressed": len(nodes), "from_events": len(events)}

        except Exception as e:
            log.warning(f"Memory compression failed: {e}")
            return {"compressed": 0, "error": str(e)}

    def get_semantic_context(self, topic: str = None, limit: int = 3) -> str:
        """Get compressed semantic memories matching topic."""
        try:
            with self._lock:
                if topic:
                    rows = self._conn.execute(
                        "SELECT * FROM semantic_memory WHERE topic LIKE ? ORDER BY importance DESC LIMIT ?",
                        (f"%{topic}%", limit)
                    ).fetchall()
                else:
                    rows = self._conn.execute(
                        "SELECT * FROM semantic_memory ORDER BY ts DESC LIMIT ?",
                        (limit,)
                    ).fetchall()

            if rows:
                snippets = [r["summary"][:120] for r in rows]
                return "Long-term: " + " | ".join(snippets)
        except Exception:
            pass
        return ""

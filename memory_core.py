"""
memory_core.py — 4-tier memory system

Tier 1 — Episodic : raw events (SQLite) → what happened
Tier 2 — Semantic : knowledge embeddings (FAISS) → what is known
Tier 3 — Procedural: tool outcomes + patterns → what works
Tier 4 — Meta     : self-knowledge, state → what I am

Design: write-cheap, read-smart. All writes go to SQLite immediately (durable).
FAISS index rebuilt lazily from SQLite on first vector query.
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
        log.info(f"Memory initialized at {self.db_path}")

    def _connect(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

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
                "INSERT INTO episodic(event_type, content, context, importance) "
                "VALUES (?,?,?,?)",
                (event_type, content[:2000], json.dumps(context or {}), importance)
            )
            self._conn.commit()
        self._faiss_dirty = True

    def search_events(self, query: str, limit: int = 5, event_type: str = None) -> list:
        """Hybrid search: vector similarity + SQL keyword fallback."""
        results = []

        # Vector search (if FAISS available)
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

    def _sql_search(self, query: str, limit: int, event_type: str = None) -> list:
        words = [w for w in query.lower().split() if len(w) > 2]
        if not words:
            with self._lock:
                rows = self._conn.execute(
                    "SELECT * FROM episodic ORDER BY ts DESC LIMIT ?",
                    (limit,)
                ).fetchall()
        else:
            conditions = " OR ".join(
                f"lower(content) LIKE '%{w}%'" for w in words[:5]
            )
            type_filter = f"AND event_type = '{event_type}'" if event_type else ""
            with self._lock:
                rows = self._conn.execute(
                    f"SELECT * FROM episodic WHERE ({conditions}) {type_filter} "
                    f"ORDER BY importance DESC, ts DESC LIMIT ?",
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

        if self._faiss_dirty or self._faiss_index is None:
            self._rebuild_faiss()

        if self._faiss_index is None or not self._faiss_texts:
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

    def _rebuild_faiss(self):
        try:
            import faiss
            import numpy as np

            model = _get_embedding_model()
            if model is None:
                return

            with self._lock:
                rows = self._conn.execute(
                    "SELECT * FROM episodic ORDER BY ts DESC LIMIT 500"
                ).fetchall()

            if not rows:
                return

            texts = [dict(r) for r in rows]
            vecs = model.encode(
                [r["content"][:256] for r in texts],
                convert_to_numpy=True
            ).astype("float32")
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
                "INSERT INTO procedural(tool,outcome,params,success,duration_ms) "
                "VALUES (?,?,?,?,?)",
                (tool, outcome[:500], json.dumps(params), int(success), duration_ms)
            )
            self._conn.commit()

    def get_tool_success_rate(self, tool: str) -> float:
        with self._lock:
            row = self._conn.execute(
                "SELECT AVG(success) FROM procedural WHERE tool=?",
                (tool,)
            ).fetchone()
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
            row = self._conn.execute(
                "SELECT value FROM meta_knowledge WHERE key=?",
                (key,)
            ).fetchone()
            if row:
                try:
                    return {"content": json.loads(row[0])}
                except Exception:
                    return {"content": row[0]}
        return {}

    def get_recent_timeline(self, limit: int = 20) -> list:
        with self._lock:
            rows = self._conn.execute(
                "SELECT ts, event_type, content FROM episodic "
                "ORDER BY ts DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def close(self):
        self._conn.close()

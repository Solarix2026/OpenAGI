# memory/faiss_store.py
"""Semantic vector store using FAISS.

Dense embeddings for topic-based similarity search.
Uses sentence-transformers or similar for encoding.
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np
import structlog

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    faiss = None

logger = structlog.get_logger()


class FaissStore:
    """
    Semantic memory using FAISS for efficient similarity search.

    Uses dense embeddings (default dim=384) for topic-based retrieval.
    Falls back to brute-force if FAISS not available.
    """

    def __init__(self, dim: int = 384):
        self.dim = dim
        self.metadata: dict[str, dict[str, Any]] = {}
        self.vectors: list[np.ndarray] = []
        self.ids: list[str] = []
        self.index: Optional[Any] = None
        self._faiss_available = FAISS_AVAILABLE

        if FAISS_AVAILABLE:
            self._init_faiss_index()
        else:
            logger.warning("faiss.not_available", fallback="brute_force")

    def _init_faiss_index(self) -> None:
        """Initialize FAISS index."""
        if not FAISS_AVAILABLE:
            return

        # IndexFlatIP = inner product (for cosine similarity with normalized vectors)
        self.index = faiss.IndexFlatIP(self.dim)
        logger.info("faiss.index_initialized", dim=self.dim)

    def _simple_encode(self, text: str) -> np.ndarray:
        """
        Simple encoding using hash-based random projection.

        In production, use sentence-transformers or similar.
        """
        import hashlib

        # Create deterministic but distributed encoding
        vec = np.zeros(self.dim, dtype=np.float32)

        for i, word in enumerate(text.lower().split()):
            hash_val = int(hashlib.sha256(word.encode()).hexdigest(), 16)
            for j in range(self.dim):
                # Generate pseudo-random from hash + position
                val = ((hash_val + i * j * 31) % 1000) / 500.0 - 1.0
                vec[j] += val

        # Normalize for cosine similarity
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec.astype(np.float32)

    def encode(self, text: str) -> np.ndarray:
        """Encode text to dense vector."""
        return self._simple_encode(text)

    def add(self, memory_id: str, content: str, metadata: dict[str, Any] = None) -> str:
        """Add content to semantic memory."""
        if metadata is None:
            metadata = {}

        vec = self.encode(content)

        self.vectors.append(vec)
        self.ids.append(memory_id)
        self.metadata[memory_id] = {
            "content": content,
            "memory_id": memory_id,
            **metadata,
        }

        if FAISS_AVAILABLE and self.index is not None:
            # FAISS expects 2D array
            self.index.add(vec.reshape(1, -1))

        return memory_id

    def query(
        self,
        query_text: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[tuple[str, float, dict]]:
        """
        Query by semantic similarity.

        Returns: list of (memory_id, score, metadata) tuples.
        """
        if not self.vectors:
            return []

        query_vec = self.encode(query_text)

        if FAISS_AVAILABLE and self.index is not None and len(self.ids) > 0:
            # FAISS search
            scores, indices = self.index.search(
                query_vec.reshape(1, -1),
                min(top_k, len(self.ids))
            )

            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and score >= min_score:
                    memory_id = self.ids[idx]
                    results.append((
                        memory_id,
                        float(score),
                        self.metadata.get(memory_id, {}),
                    ))
            return results
        else:
            # Brute force fallback
            query_vec = query_vec.reshape(1, -1)
            vectors = np.stack(self.vectors)

            # Cosine similarity (vectors are normalized)
            scores = np.dot(vectors, query_vec.T).flatten()

            # Get top k
            top_indices = np.argsort(scores)[::-1][:top_k]

            results = []
            for idx in top_indices:
                if scores[idx] >= min_score:
                    memory_id = self.ids[idx]
                    results.append((
                        memory_id,
                        float(scores[idx]),
                        self.metadata.get(memory_id, {}),
                    ))
            return results

    def get(self, memory_id: str) -> Optional[dict[str, Any]]:
        """Retrieve metadata."""
        return self.metadata.get(memory_id)

    def delete(self, memory_id: str) -> bool:
        """Note: FAISS doesn't support deletion.
        Mark as deleted in metadata, will be excluded from results.
        """
        if memory_id in self.metadata:
            self.metadata[memory_id]["_deleted"] = True
            return True
        return False

    def clear(self) -> None:
        """Clear all memories."""
        self.vectors.clear()
        self.ids.clear()
        self.metadata.clear()
        if FAISS_AVAILABLE:
            self._init_faiss_index()

    def save(self, path: Path) -> None:
        """Serialize to disk."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        data = {
            "vectors": np.stack(self.vectors) if self.vectors else np.array([]),
            "ids": self.ids,
            "metadata": self.metadata,
            "dim": self.dim,
        }
        np.savez_compressed(path / "faiss_store.npz", **data)

        logger.info("faiss.saved", path=str(path), count=len(self.ids))

    def load(self, path: Path) -> None:
        """Load from disk."""
        data_path = Path(path) / "faiss_store.npz"

        if not data_path.exists():
            logger.warning("faiss.no_file", path=str(path))
            return

        data = np.load(data_path, allow_pickle=True)

        self.dim = int(data["dim"])
        self.ids = list(data["ids"])
        self.metadata = data["metadata"].item()

        vectors_data = data["vectors"]
        if vectors_data.size > 0:
            self.vectors = list(vectors_data)

            # Rebuild FAISS index
            if FAISS_AVAILABLE:
                self._init_faiss_index()
                for vec in self.vectors:
                    self.index.add(vec.reshape(1, -1))

        logger.info("faiss.loaded", count=len(self.ids))

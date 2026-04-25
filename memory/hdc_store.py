# memory/hdc_store.py
"""Hyperdimensional Computing (HDC) hypervector store.

Pure numpy, no external dependencies.
Fast associative recall via XOR binding and majority bundling.

HDC uses 10,000-dimensional binary vectors:
- Encoding: random projection + threshold
- Binding: XOR operation
- Bundling: majority vote (element-wise)
- Similarity: Hamming distance
"""
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import numpy as np
import structlog

logger = structlog.get_logger()


class HDCStore:
    """
    HDC Memory Store using binary hypervectors.

    Memory is represented as high-dimensional binary vectors.
    - Fast: Hamming distance computation is just XOR + popcount
    - Robust: Noise-tolerant, similar patterns bind together
    - Hardware-efficient: Bit operations, minimal storage
    """

    def __init__(self, dim: int = 10000, seed: int = 42):
        self.dim = dim
        self.rng = np.random.RandomState(seed)
        self.memories: dict[str, np.ndarray] = {}
        self.metadata: dict[str, dict[str, Any]] = {}
        self.item_base: dict[str, np.ndarray] = {}  # Base vectors for items
        self._initialized = True

    def _generate_item_vector(self, item_id: str) -> np.ndarray:
        """Generate a random item vector for encoding."""
        if item_id not in self.item_base:
            # Deterministic but pseudo-random per item
            np.random.seed(hash(item_id) & 0xFFFFFFFF)
            self.item_base[item_id] = np.random.randint(0, 2, self.dim).astype(np.bool_)
            np.random.seed(None)  # Reset
        return self.item_base[item_id].copy()

    def encode(self, text: str) -> np.ndarray:
        """
        Encode text into HDC hypervector.

        Strategy: n-gram encoding with binding and bundling.
        """
        if not text:
            return np.zeros(self.dim, dtype=np.bool_)

        tokens = text.lower().split()
        if len(tokens) == 0:
            return np.zeros(self.dim, dtype=np.bool_)

        # Encode each token
        vectors = []
        for token in tokens:
            # Hash-based encoding
            token_bytes = token.encode("utf-8")
            rng_seed = int(hashlib.md5(token_bytes).hexdigest(), 16) & 0xFFFFFFFF

            np.random.seed(rng_seed)
            vec = np.random.randint(0, 2, self.dim).astype(np.bool_)
            vectors.append(vec)

        # Bundle with majority vote
        bundled = self.bundle(vectors)
        return bundled

    def bind(self, hv1: np.ndarray, hv2: np.ndarray) -> np.ndarray:
        """XOR binding of two hypervectors."""
        return np.logical_xor(hv1, hv2)

    def bundle(self, hvs: list[np.ndarray]) -> np.ndarray:
        """
        Bundle multiple hypervectors via majority voting.

        Each position: 1 if majority of vectors have 1, else 0.
        """
        if not hvs:
            return np.zeros(self.dim, dtype=np.bool_)

        stacked = np.stack(hvs)
        summed = np.sum(stacked, axis=0)
        # Majority vote
        return summed >= (len(hvs) / 2)

    def similarity(self, hv1: np.ndarray, hv2: np.ndarray) -> float:
        """
        Compute Hamming similarity (1 - normalized Hamming distance).

        Returns 1.0 for identical, 0.0 for completely different.
        """
        return 1.0 - np.mean(np.logical_xor(hv1, hv2))

    def cosine_similarity(self, hv1: np.ndarray, hv2: np.ndarray) -> float:
        """Cosine similarity (equivalent for binary vectors with normalization)."""
        return self.similarity(hv1, hv2) * 2 - 1  # Map [0,1] to [-1,1]

    def add(self, memory_id: str, content: str, metadata: dict[str, Any] = None) -> str:
        """Store content in HDC memory."""
        if metadata is None:
            metadata = {}

        hv = self.encode(content)
        self.memories[memory_id] = hv
        self.metadata[memory_id] = {
            "content": content,
            "memory_id": memory_id,
            **metadata,
        }

        return memory_id

    def query(self, query_text: str, top_k: int = 5) -> list[tuple[str, float, dict]]:
        """
        Query by text similarity.

        Returns: list of (memory_id, similarity_score, metadata) tuples.
        """
        query_hv = self.encode(query_text)

        if not self.memories:
            return []

        # Compute similarities
        scores = []
        for memory_id, hv in self.memories.items():
            sim = self.similarity(query_hv, hv)
            scores.append((memory_id, sim, self.metadata.get(memory_id, {})))

        # Sort by similarity descending
        scores.sort(key=lambda x: (-x[1], x[0]))

        return scores[:top_k]

    def get(self, memory_id: str) -> Optional[dict[str, Any]]:
        """Retrieve metadata for a memory."""
        return self.metadata.get(memory_id)

    def delete(self, memory_id: str) -> bool:
        """Delete a memory."""
        if memory_id in self.memories:
            del self.memories[memory_id]
            del self.metadata[memory_id]
            return True
        return False

    def clear(self) -> None:
        """Clear all memories."""
        self.memories.clear()
        self.metadata.clear()

    def save(self, path: Path) -> None:
        """Serialize to disk."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        # Save as compressed numpy
        data = {
            "memories": {k: v.astype(np.uint8) for k, v in self.memories.items()},
            "metadata": self.metadata,
            "dim": self.dim,
        }
        np.savez_compressed(path / "hdc_store.npz", **data)

        logger.info("hdc.saved", path=str(path), count=len(self.memories))

    def load(self, path: Path) -> None:
        """Load from disk."""
        path = Path(path) / "hdc_store.npz"

        if not path.exists():
            logger.warning("hdc.no_file", path=str(path))
            return

        data = np.load(path, allow_pickle=True)

        self.dim = int(data["dim"])
        self.memories = {k: v.astype(np.bool_) for k, v in data["memories"].item().items()}
        self.metadata = data["metadata"].item()

        logger.info("hdc.loaded", count=len(self.memories))

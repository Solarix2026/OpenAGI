# Copyright (c) 2026 Solarix2026
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""
tool_registry.py — Dynamic tool registration and semantic search

Tools register themselves. Kernel discovers them via list_tools().
_classify() receives the live tool list — no hardcoded tool names.
"""
import logging
import os
from dataclasses import dataclass, field
from typing import Callable, Optional, Any
import numpy as np

log = logging.getLogger("ToolRegistry")

# Global encoder cache — load ONCE, reuse forever
_ENCODER = None
_ENCODER_LOAD_ATTEMPTED = False

def _get_encoder():
    """Get cached SentenceTransformer encoder (loads only once, deferred)."""
    global _ENCODER, _ENCODER_LOAD_ATTEMPTED
    if _ENCODER_LOAD_ATTEMPTED:
        return _ENCODER
    _ENCODER_LOAD_ATTEMPTED = True

    # Skip on Python 3.14+ due to transformers/importlib.metadata incompatibility
    import sys
    if sys.version_info >= (3, 14) and not os.environ.get("FORCE_ENCODER"):
        log.warning("Python 3.14+ detected - semantic search disabled (set FORCE_ENCODER=1 to override)")
        return None

    if os.environ.get("OPENAGI_NO_ENCODER"):
        return None

    try:
        from sentence_transformers import SentenceTransformer
        _ENCODER = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        log.info("Tool encoder loaded (cached)")
    except Exception as e:
        log.warning(f"Could not load encoder: {e}")
        _ENCODER = None
    return _ENCODER


@dataclass
class ToolSpec:
    name: str
    func: Callable
    description: str
    parameters: dict = field(default_factory=dict)
    category: str = "general"
    call_count: int = 0
    success_count: int = 0

    def success_rate(self) -> float:
        return self.success_count / self.call_count if self.call_count else 0.0


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolSpec] = {}
        self._embeddings: dict[str, np.ndarray] = {}
        log.info("ToolRegistry initialized")

    def register(self, name: str, func: Callable, description: str, parameters: dict = None, category: str = "general"):
        spec = ToolSpec(
            name=name,
            func=func,
            description=description,
            parameters=parameters or {},
            category=category
        )
        self._tools[name] = spec

        # Embed description for semantic search (uses cached encoder, deferred)
        try:
            enc = _get_encoder()
            if enc:
                self._embeddings[name] = enc.encode([description])[0]
        except Exception:
            pass  # Continue without embeddings if encoder fails
        log.debug(f"Registered tool: {name}")

    def execute(self, name: str, params: dict) -> dict:
        spec = self._tools.get(name)
        if not spec:
            return {"success": False, "error": f"Tool '{name}' not found"}

        spec.call_count += 1
        try:
            result = spec.func(params)
            if isinstance(result, dict) and result.get("success", True):
                spec.success_count += 1
            return result if isinstance(result, dict) else {"success": True, "data": result}
        except Exception as e:
            log.error(f"Tool {name} error: {e}")
            return {"success": False, "error": str(e)}

    def search(self, query: str, top_k: int = 3) -> list[str]:
        """Semantic tool search — returns tool names most relevant to query."""
        enc = _get_encoder()
        if enc and self._embeddings:
            try:
                q_vec = enc.encode([query])[0]
                scores = {
                    name: float(np.dot(q_vec, emb) / (np.linalg.norm(q_vec) * np.linalg.norm(emb) + 1e-9))
                    for name, emb in self._embeddings.items()
                }
                return sorted(scores, key=scores.get, reverse=True)[:top_k]
            except Exception:
                pass

        # Keyword fallback
        q_words = set(query.lower().split())
        scored = []
        for name, spec in self._tools.items():
            desc_words = set(spec.description.lower().split())
            score = len(q_words & desc_words)
            if score:
                scored.append((score, name))
        scored.sort(reverse=True)
        return [n for _, n in scored[:top_k]]

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def get_tool_descriptions(self) -> str:
        """Compact string for _classify() prompt."""
        lines = []
        for name, spec in self._tools.items():
            lines.append(f"  {name}: {spec.description[:80]}")
        return "\n".join(lines)

    def get_tool_info(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

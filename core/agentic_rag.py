# Copyright (c) 2026 HackerTMJ
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""
core/agentic_rag.py — Agentic Memory Retrieval with latency optimization

Goal: Multi-hop reasoning without adding >500ms latency to hot path.

Strategy:
1. Fast path (~50ms): Vector search + confidence threshold
2. Smart path (~200ms): Plan + refine (only if fast path misses)
3. Full agentic (~400ms): Multi-hop (only for complex queries)
"""

import time
import json
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

log = logging.getLogger("AgenticRAG")


@dataclass
class RetrievedMemory:
    content: str
    source: str
    relevance_score: float
    timestamp: float
    event_type: str


@dataclass
class RetrievalPlan:
    """Planned retrieval strategy."""
    primary_keywords: List[str]
    expand_queries: List[str]
    needs_multi_hop: bool
    hop_targets: List[str]
    confidence_threshold: float


class AgenticMemoryRAG:
    """
    Agentic RAG with tiered latency optimization.

    Tiers:
    - T1 Fast (50ms): Single vector search, high confidence
    - T2 Smart (200ms): Query expansion + re-ranking
    - T3 Agentic (400ms): Multi-hop reasoning
    """

    def __init__(self, memory_core, call_nvidia_func):
        self.memory = memory_core
        self.call_nvidia = call_nvidia_func

        # Strategy cache: query_hash -> RetrievalPlan
        self._strategy_cache: Dict[str, RetrievalPlan] = {}
        self._cache_hits = 0
        self._cache_misses = 0

        # Latency budgets (seconds)
        self.t1_budget = 0.05   # 50ms
        self.t2_budget = 0.20   # 200ms
        self.t3_budget = 0.40   # 400ms

        # Confidence thresholds
        self.t1_threshold = 0.75
        self.t2_threshold = 0.60

    def retrieve(
        self,
        query: str,
        context: str = "",
        max_budget_ms: int = 250,
        force_agentic: bool = False
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Retrieve with automatic tier selection.

        Returns: (context_string, metadata)
        """
        t0 = time.time()
        metadata = {"tier": "none", "latency_ms": 0, "memories_retrieved": 0}

        # Pre-process query to understand complexity
        complexity = self._assess_complexity(query)
        metadata["complexity"] = complexity

        # ===== TIER 1: Fast Path (vector only) =====
        if complexity == "simple" and not force_agentic:
            candidates = self._vector_search(query, top_k=5)
            t1_latency = (time.time() - t0) * 1000

            if candidates and candidates[0].relevance_score >= self.t1_threshold:
                result = self._format_memories(candidates[:3])
                metadata.update({
                    "tier": "t1_fast",
                    "latency_ms": t1_latency,
                    "memories_retrieved": len(candidates)
                })
                log.debug(f"[RAG] T1 hit: {t1_latency:.0f}ms")
                return result, metadata

            # Almost good enough - try cheap re-ranking
            if t1_latency < self.t2_budget * 1000:
                reranked = self._fast_rerank(query, candidates)
                if reranked and reranked[0].relevance_score >= self.t1_threshold:
                    result = self._format_memories(reranked[:3])
                    metadata.update({
                        "tier": "t1_rerank",
                        "latency_ms": (time.time() - t0) * 1000,
                        "memories_retrieved": len(reranked)
                    })
                    return result, metadata

        # ===== TIER 2: Smart Path (plan + expand) =====
        remaining_budget = max_budget_ms - (time.time() - t0) * 1000

        if remaining_budget > 150 or complexity == "multi_entity":
            plan = self._get_or_create_plan(query, context)

            # Parallel retrieval with expanded queries
            all_candidates = []
            for eq in plan.expand_queries[:2]:
                all_candidates.extend(self._vector_search(eq, top_k=3))

            # Deduplicate
            seen = set()
            unique = []
            for c in all_candidates:
                if c.source not in seen:
                    unique.append(c)
                    seen.add(c.source)

            # Fast LLM re-rank (1 call, ~100ms)
            reranked = self._llm_rerank(query, unique, budget_calls=1)
            t2_latency = (time.time() - t0) * 1000

            if reranked and reranked[0].relevance_score >= self.t2_threshold:
                result = self._format_memories(reranked[:4])
                metadata.update({
                    "tier": "t2_smart",
                    "latency_ms": t2_latency,
                    "memories_retrieved": len(reranked)
                })
                log.debug(f"[RAG] T2 hit: {t2_latency:.0f}ms")
                return result, metadata

        # ===== TIER 3: Agentic Path (multi-hop) =====
        remaining_budget = max_budget_ms - (time.time() - t0) * 1000

        if (remaining_budget > 200 or force_agentic) and complexity in ("multi_hop", "multi_entity"):
            return self._agentic_multi_hop(query, context, t0, metadata)

        # Fallback: return best of what we have
        result = self._format_memories(reranked[:3] if 'reranked' in dir() else candidates[:2])
        metadata.update({
            "tier": "t2_fallback",
            "latency_ms": (time.time() - t0) * 1000,
            "memories_retrieved": len(reranked) if 'reranked' in dir() else len(candidates)
        })
        return result, metadata

    def _assess_complexity(self, query: str) -> str:
        """
        Query complexity assessment (cheap, no LLM).
        Returns: 'simple' | 'multi_entity' | 'multi_hop'
        """
        q = query.lower()

        # Multi-hop indicators
        multi_hop_patterns = [
            "what did we discuss about",
            "when did I last mention",
            "based on",
            "therefore",
            "combine with",
        ]
        if any(p in q for p in multi_hop_patterns):
            return "multi_hop"

        # Multi-entity indicators
        entity_count = sum(q.count(e) for e in [" and ", " or ", ",", "compare"])
        if entity_count >= 2:
            return "multi_entity"

        # Simple queries
        if len(query.split()) < 6:
            return "simple"

        return "simple"

    def _vector_search(self, query: str, top_k: int = 5) -> List[RetrievedMemory]:
        """Fast vector similarity search."""
        try:
            events = self.memory.get_relevant_memory_context(query, top_n=top_k)
            results = []

            scores = [1.0, 0.85, 0.70, 0.55, 0.40][:len(events)]
            for i, event in enumerate(events):
                if isinstance(event, dict):
                    results.append(RetrievedMemory(
                        content=event.get("content", ""),
                        source=str(event.get("id", "unknown")),
                        relevance_score=scores[i],
                        timestamp=event.get("ts", 0),
                        event_type=event.get("event_type", "unknown")
                    ))

            return results
        except Exception as e:
            log.debug(f"Vector search failed: {e}")
            return []

    def _fast_rerank(self, query: str, candidates: List[RetrievedMemory]) -> List[RetrievedMemory]:
        """Fast keyword-based reranking (no LLM)."""
        if not candidates:
            return []

        query_terms = set(query.lower().split())

        for c in candidates:
            content_terms = set(c.content.lower().split())
            overlap = len(query_terms & content_terms)
            # Boost score based on keyword overlap
            c.relevance_score += 0.1 * overlap

        return sorted(candidates, key=lambda x: x.relevance_score, reverse=True)

    def _get_or_create_plan(self, query: str, context: str) -> RetrievalPlan:
        """Get cached plan or create new one."""
        query_hash = self._hash_query(query, context)

        if query_hash in self._strategy_cache:
            return self._strategy_cache[query_hash]

        plan = self._create_plan(query, context)
        self._strategy_cache[query_hash] = plan

        # Cache LRU: keep only 100 strategies
        if len(self._strategy_cache) > 100:
            oldest = list(self._strategy_cache.keys())[0]
            del self._strategy_cache[oldest]

        return plan

    def _create_plan(self, query: str, context: str) -> RetrievalPlan:
        """Create retrieval plan via lightweight LLM or heuristic."""
        # Fast heuristic planning for common patterns
        q = query.lower()

        if "compare" in q:
            return RetrievalPlan(
                primary_keywords=[q],
                expand_queries=[q + " difference", q + " similarity"],
                needs_multi_hop=False,
                hop_targets=[],
                confidence_threshold=0.65
            )

        if "when" in q or "last" in q:
            return RetrievalPlan(
                primary_keywords=[q],
                expand_queries=[q + " date", q + " time"],
                needs_multi_hop=False,
                hop_targets=[],
                confidence_threshold=0.70
            )

        # Default plan
        return RetrievalPlan(
            primary_keywords=[q],
            expand_queries=[q],
            needs_multi_hop=False,
            hop_targets=[],
            confidence_threshold=0.60
        )

    def _llm_rerank(self, query: str, candidates: List[RetrievedMemory], budget_calls: int = 1) -> List[RetrievedMemory]:
        """Fast LLM-based reranking."""
        if not candidates or not self.call_nvidia:
            return candidates

        # Batch all candidates into one call for efficiency
        candidates_text = "\n---\n".join([
            f"[{i}] {c.event_type}: {c.content[:80]}"
            for i, c in enumerate(candidates)
        ])

        prompt = f"""Rate relevance of each memory to query. Return JSON: {{"scores": [0-10, 0-10,...]}}

Query: "{query}"

Memories:
{candidates_text}

Return: {{"scores": [___]}} (one score per memory)"""

        try:
            start = time.time()
            response = self.call_nvidia(
                [{"role": "user", "content": prompt}],
                max_tokens=100,
                fast=True
            )

            # Timeout check
            if time.time() - start > 0.15:  # 150ms budget
                log.debug("[RAG] LLM rerank timeout, using scores unchanged")
                return candidates

            # Parse scores
            m = re.search(r'"scores"\s*:\s*\[(.*?)\]', response, re.DOTALL)
            if m:
                scores_str = f"[{m.group(1)}]"
                llm_scores = json.loads(scores_str)

                # Blend scores: 60% original, 40% LLM
                for i, c in enumerate(candidates):
                    if i < len(llm_scores):
                        llm_score = llm_scores[i] / 10.0  # 0-10 -> 0-1
                        c.relevance_score = 0.6 * c.relevance_score + 0.4 * llm_score

        except Exception as e:
            log.debug(f"LLM rerank failed: {e}")

        return sorted(candidates, key=lambda x: x.relevance_score, reverse=True)

    def _agentic_multi_hop(
        self,
        query: str,
        context: str,
        t0: float,
        metadata: Dict
    ) -> Tuple[str, Dict]:
        """Full multi-hop Agentic RAG."""
        log.info("[RAG] Entering Tier 3: Multi-hop reasoning")

        # Step 1: Initial retrieval
        hop1 = self._vector_search(query, top_k=3)

        # Step 2: Generate follow-up queries
        if not hop1:
            return self._format_memories([]), {**metadata, "tier": "t3_empty"}

        # Check time budget
        if (time.time() - t0) * 1000 > 350:
            return self._format_memories(hop1), {**metadata, "tier": "t3_timeout_h1"}

        # Generate hop queries (1 call, ~120ms)
        hop1_summary = " | ".join([h.content[:40] for h in hop1[:2]])
        followup_prompt = f"""Given query and initial results, generate 2 follow-up searches.

Query: "{query}"
Found: {hop1_summary}

Missing context? Generate 2 additional search queries to complete the answer.
Return JSON: {{"followup_queries": ["query1", "query2"]}}"""

        try:
            response = self.call_nvidia(
                [{"role": "user", "content": followup_prompt}],
                max_tokens=100,
                fast=True
            )
            m = re.search(r'"followup_queries".*?(\[.*?\])', response, re.DOTALL)
            if m:
                followup = json.loads(m.group(1))
            else:
                followup = []
        except:
            followup = []

        # Step 3: Execute follow-up searches
        hop2 = []
        for fq in followup[:2]:
            hop2.extend(self._vector_search(fq, top_k=2))

        # Deduplicate hop1 + hop2
        all_memories = {m.source: m for m in (hop1 + hop2)}
        final_list = sorted(all_memories.values(), key=lambda x: x.relevance_score, reverse=True)[:5]

        t3_latency = (time.time() - t0) * 1000

        result = self._format_memories(final_list)
        metadata.update({
            "tier": "t3_agentic",
            "latency_ms": t3_latency,
            "memories_retrieved": len(final_list),
            "hops": 2,
            "hop_queries": len(followup)
        })

        log.info(f"[RAG] T3 complete: {t3_latency:.0f}ms, {len(final_list)} memories")
        return result, metadata

    def _hash_query(self, query: str, context: str) -> str:
        """Simple hash for plan caching."""
        import hashlib
        combined = (query + "|" + context[:50]).lower().strip()
        return hashlib.md5(combined.encode()).hexdigest()[:16]

    def _format_memories(self, memories: List[RetrievedMemory]) -> str:
        """Format memories for context injection."""
        if not memories:
            return ""

        lines = []
        for i, m in enumerate(memories):
            ago = "recent"
            lines.append(f"[{i+1}] {m.content[:150]}")

        return "\n".join(["Relevant memory:"] + lines)

    def get_statistics(self) -> Dict[str, Any]:
        """Return module statistics."""
        return {
            "strategy_cache_size": len(self._strategy_cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": self._cache_hits / (self._cache_hits + self._cache_misses) if (self._cache_hits + self._cache_misses) > 0 else 0
        }
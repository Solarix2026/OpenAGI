# Copyright (c) 2026 ApeironAI
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""
causal_engine.py — Causal reasoning from execution history

Builds a directed acyclic graph (DAG) of cause-effect relationships
by analyzing episodic memory event sequences.

Primary use: understand WHY tools fail and HOW to prevent recurrence.
Secondary use: counterfactual — "if I had used tool X instead of Y..."
"""
import json
import logging
import re
from collections import defaultdict

log = logging.getLogger("CausalEngine")


class CausalEngine:
    def __init__(self, memory):
        self.memory = memory
        self._dag = defaultdict(list)  # cause_event_id → [effect_event_id]

    def build_dag_from_recent(self, window=50) -> dict:
        """
        Analyze last N events. For consecutive action→outcome pairs,
        infer causal links. Store in memory meta_knowledge["causal_dag"].
        """
        from core.llm_gateway import call_nvidia
        events = self.memory.get_recent_timeline(limit=window)
        events_text = "\n".join(
            f"{i}. [{e['event_type']}] {e['content'][:80]}"
            for i, e in enumerate(events)
        )
        prompt = f"""Analyze this sequence of AI agent events and identify causal relationships.

Events: {events_text}

Find: action A caused outcome B (especially failures).

Return JSON: {{"causal_links": [{{"cause": "event description", "effect": "what happened", "type": "success|failure|partial"}}]}}"""
        raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=800)
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        dag = json.loads(m.group(0)) if m else {"causal_links": []}
        self.memory.update_meta_knowledge("causal_dag", dag)
        return dag

    def counterfactual(self, failed_action: str, alternative: str) -> str:
        """
        What would have happened if we used `alternative` instead of `failed_action`?
        Returns NVIDIA reasoning as string.
        """
        from core.llm_gateway import call_nvidia
        dag = self.memory.get_meta_knowledge("causal_dag")
        dag_data = dag.get("content", {}) if dag else {}
        prompt = f"""Counterfactual reasoning for an AI agent:

What actually happened: {failed_action}
Alternative approach: {alternative}

Known causal patterns: {json.dumps(dag_data)[:300]}

What would most likely have happened with the alternative approach?
Be specific about the outcome difference. 2-3 sentences."""
        return call_nvidia([{"role": "user", "content": prompt}], max_tokens=200, fast=True)

    def why_did_fail(self, tool_name: str) -> str:
        """Explain root cause of a tool's failures using causal analysis."""
        from core.llm_gateway import call_nvidia
        outcomes = self.memory.search_events(tool_name, limit=10, event_type="tool_outcome")
        failures = [e for e in outcomes if "fail" in e.get("content", "").lower()]
        if not failures:
            return f"No failure history found for {tool_name}."
        patterns = "\n".join(f.get("content", "")[:100] for f in failures[:5])
        prompt = f"""Analyze why tool '{tool_name}' keeps failing:

Failure history: {patterns}

Root cause in 2 sentences. Be specific."""
        return call_nvidia([{"role": "user", "content": prompt}], max_tokens=150, fast=True)

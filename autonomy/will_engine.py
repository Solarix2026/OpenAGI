# Copyright (c) 2026 Solarix2026
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""
will_engine.py — Three autonomous drives that generate goals WITHOUT user input

Conatus (Spinoza) = self-preservation
- Scans tool failure rates every 2h. If tool success_rate < 0.4 → goal: repair/replace it
- Checks memory staleness. If no new events > 8h → goal: refresh world knowledge
- Monitors goal queue stagnation. Unchanged pending goal > 24h → goal: reassess it

Telos (Aristotle) = final cause / mission alignment
- Persistent mission stored in meta_knowledge["telos"]
- Every proposed goal scored 0-1 against Telos via NVIDIA
- Goals scoring < 0.3 rejected before entering queue

Dialectic (Hegel) = synthesis through contradiction
- Takes any topic/behavior/belief
- Generates: Thesis (current state) → Antithesis (strongest failure mode) → Synthesis (integrated fix)
- Used by CHRONOS_REVERIE for nightly self-critique
"""
import json
import logging
from typing import Optional
from datetime import datetime

log = logging.getLogger("Will")


class WillEngine:
    def __init__(self, memory, registry, add_goal_fn):
        """
        Args:
            memory: memory_core.Memory instance
            registry: tool_registry.ToolRegistry instance
            add_goal_fn: callable(description, priority, source) -> dict
        """
        self.memory = memory
        self.registry = registry
        self.add_goal = add_goal_fn
        self._telos = self._load_or_init_telos()

    def _load_or_init_telos(self) -> str:
        """Load Telos from meta_knowledge or create default."""
        try:
            meta = self.memory.get_meta_knowledge("telos")
            if meta and meta.get("content"):
                return str(meta["content"])
        except Exception:
            pass

        default = "Expand autonomous capability: understand more, act more precisely, evolve continuously without human prompting."
        try:
            self.memory.update_meta_knowledge("telos", default)
        except Exception:
            pass
        return default

    def get_telos(self) -> str:
        """Get current mission statement."""
        return self._telos

    def update_telos(self, new_telos: str):
        """Update mission statement."""
        self._telos = new_telos
        try:
            self.memory.update_meta_knowledge("telos", new_telos)
        except Exception as e:
            log.warning(f"Failed to save telos: {e}")

    def conatus_check(self) -> list[dict]:
        """Scan for threats to system capability. Return new goals to add."""
        new_goals = []

        # Tool health monitoring
        try:
            for name in self.registry.list_tools():
                spec = self.registry.get_tool_info(name)
                if spec and spec.call_count >= 5 and spec.success_rate() < 0.4:
                    new_goals.append({
                        "description": f"Tool '{name}' failing ({spec.success_rate():.0%}). Diagnose and fix or invent replacement.",
                        "priority": 0.85,
                        "source": "conatus"
                    })
        except Exception as e:
            log.debug(f"Tool health check error: {e}")

        # Memory staleness check
        try:
            recent = self.memory.get_recent_timeline(limit=1)
            if recent:
                last_ts = recent[0].get("ts", "")
                if last_ts:
                    delta = (datetime.now() - datetime.fromisoformat(last_ts.replace("Z", ""))).total_seconds() / 3600
                    if delta > 8:
                        # Check if this goal already exists
                        from core.goal_persistence import load_goal_queue
                        existing = [g.get("description", "") for g in load_goal_queue() if g.get("status") in ("pending", "active")]
                        goal_desc = "Memory stale >8h. Fetch world events and run context refresh."
                        if not any(goal_desc[:30] in e or e[:30] in goal_desc for e in existing):
                            new_goals.append({
                                "description": goal_desc,
                                "priority": 0.5,
                                "source": "conatus"
                            })
        except Exception as e:
            log.debug(f"Memory staleness check error: {e}")

        # Goal queue stagnation check
        try:
            from core.goal_persistence import load_goal_queue
            goals = load_goal_queue()
            for goal in goals:
                if goal.get("status") == "pending":
                    created = goal.get("created_at", "")
                    if created:
                        age_hours = (datetime.now() - datetime.fromisoformat(created)).total_seconds() / 3600
                        if age_hours > 24:
                            new_goals.append({
                                "description": f"Goal '{goal.get('description', 'unknown')[:50]}' stale >24h. Reassess priority.",
                                "priority": 0.6,
                                "source": "conatus"
                            })
                            break  # Only one stale goal goal
        except Exception as e:
            log.debug(f"Goal stagnation check error: {e}")

        return new_goals

    def telos_align(self, goal_description: str) -> float:
        """Score goal alignment with system mission. Reject < 0.3."""
        try:
            from core.llm_gateway import call_nvidia
            import re

            prompt = f'''Mission: "{self._telos}"
Proposed goal: "{goal_description}"
Score alignment 0.0-1.0. Return JSON: {{"score": 0.7}}'''

            resp = call_nvidia([{"role": "user", "content": prompt}], max_tokens=80, fast=True)
            m = re.search(r'"score":\s*([\d.]+)', resp)
            if m:
                return float(m.group(1))
        except Exception as e:
            log.debug(f"Telos alignment check failed: {e}")

        return 0.5  # Default acceptance on failure

    def dialectic_review(self, topic: str) -> dict:
        """Hegelian dialectic: thesis → antithesis → synthesis → action_item."""
        try:
            from core.llm_gateway import call_nvidia
            import re

            prompt = f'''Apply Hegelian dialectic for AI self-improvement on: "{topic}"

Thesis: current state/approach
Antithesis: strongest failure mode or counterargument
Synthesis: integrated improvement

Return JSON: {{"thesis":"...","antithesis":"...","synthesis":"...","action_item":"concrete change to implement"}}'''

            raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=500)
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                return json.loads(m.group(0))
        except Exception as e:
            log.error(f"Dialectic failed: {e}")

        return {}

    def run_will_cycle(self) -> list[dict]:
        """Conatus check → Telos filter → add approved goals. Returns added goals."""
        candidates = self.conatus_check()
        added = []
        for g in candidates:
            score = self.telos_align(g["description"])
            if score >= 0.3:
                try:
                    self.add_goal(g["description"], g["priority"] * score, g["source"])
                    added.append({**g, "telos_score": score})
                    log.info(f"[WILL] Added goal: {g['description'][:60]} (score: {score:.2f})")
                except Exception as e:
                    log.error(f"Failed to add goal: {e}")
        return added

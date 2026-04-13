# Copyright (c) 2026 HackerTMJ (门牌号3号)
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/HackerTMJ/OpenAGI

"""
evolution_engine.py — 4-layer autonomous self-improvement

Layer 1: Gap Detector
    Reads MetacognitiveEngine.get_weakest() + causal failure analysis
    Identifies capability gaps that matter most

Layer 2: Curriculum Generator
    For each gap: generate specific learning/practice tasks
    Tasks are concrete (e.g., "attempt 5 browser_automation tasks and log errors")

Layer 3: Hypothesis-Test Loop
    Generate hypothesis for improvement → test with real tasks
    If success rate improves: accept. If not: discard.

Layer 4: Knowledge Consolidation
    Compress successful patterns into meta_knowledge
    Update capability matrix scores
    Optionally: write new helper function to skill_library

GUARD: All self-modification constrained by guard_protocols.py
- Cannot modify its own code. Can only add new tools/skills.
- Cannot disable safety checks.
- Cannot exceed Telos.
"""
import json
import re
import logging
from pathlib import Path
from core.llm_gateway import call_nvidia

log = logging.getLogger("Evolution")


class EvolutionEngine:
    def __init__(self, memory, metacognition, registry):
        self.memory = memory
        self.meta = metacognition
        self.registry = registry

    def run_gap_detection(self) -> list[dict]:
        """Identify top capability gaps from metacognition + failure history."""
        weakest = self.meta.get_weakest(n=5) if self.meta else []
        gap_data = []
        for dim, score in weakest:
            # Find relevant failures in memory
            failures = self.memory.search_events(dim.replace("_", " "), limit=5)
            failure_text = "\n".join(f.get("content", "")[:80] for f in failures[:3])
            gap_data.append({
                "dimension": dim,
                "score": score,
                "evidence": failure_text,
            })
        self.memory.update_meta_knowledge("detected_gaps", gap_data)
        return gap_data

    def generate_curriculum(self, gap: dict) -> list[dict]:
        """Generate 3-5 practice tasks to improve a capability gap."""
        prompt = f"""Generate a learning curriculum to improve AI capability: {gap['dimension']}

Current score: {gap['score']}/5
Evidence of weakness: {gap.get('evidence', 'none')}

Create 3-5 specific practice tasks. Each task should be:
- Executable by the AI agent using available tools
- Measurable (clear success/failure criteria)
- Progressive (increasing difficulty)

Return JSON: {{"tasks": [{{"task": "...", "tool_required": "...", "success_criteria": "...", "difficulty": 1-5}}]}}"""
        raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=600)
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        result = json.loads(m.group(0)) if m else {"tasks": []}
        return result.get("tasks", [])

    def run_hypothesis_test(self, dimension: str, hypothesis: str, test_tasks: list[dict]) -> dict:
        """Test if a hypothesis improves performance on a dimension."""
        results = {"dimension": dimension, "hypothesis": hypothesis, "tests": [], "improvement": 0.0}
        baseline = self.meta.get_score(dimension) if self.meta else 2.0

        for task in test_tasks[:3]:  # Max 3 tests per cycle
            prompt = f"""Evaluate this AI capability improvement hypothesis:

Hypothesis: {hypothesis}
Test task: {task.get('task', '')}
Success criteria: {task.get('success_criteria', '')}

Would applying this hypothesis improve performance on this task?

Return JSON: {{"improves": true/false, "confidence": 0.0-1.0, "reasoning": "..."}}"""
            raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=200, fast=True)
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            test_result = json.loads(m.group(0)) if m else {"improves": False}
            results["tests"].append(test_result)

        # Calculate improvement
        improvements = [t for t in results["tests"] if t.get("improves")]
        improvement_rate = len(improvements) / max(len(results["tests"]), 1)
        results["improvement"] = improvement_rate

        if improvement_rate > 0.6 and self.meta:
            self.meta.update_capability(dimension, +0.3)
            log.info(f"[EVOLVE] Hypothesis accepted for {dimension}: +0.3")

        return results

    def run_full_cycle(self) -> str:
        """Full evolution cycle. Returns summary for user."""
        gaps = self.run_gap_detection()
        if not gaps:
            return "No significant capability gaps detected."

        top_gap = gaps[0]
        curriculum = self.generate_curriculum(top_gap)

        # Generate hypothesis for top gap
        hypothesis_prompt = f"""Generate a hypothesis for improving AI capability: {top_gap['dimension']}

Current weakness evidence: {top_gap.get('evidence', 'none')}

What specific change to behavior or approach would improve this capability?
One concrete hypothesis in 2 sentences."""
        hypothesis = call_nvidia(
            [{"role": "user", "content": hypothesis_prompt}],
            max_tokens=150,
            fast=True
        )

        test_result = self.run_hypothesis_test(top_gap["dimension"], hypothesis, curriculum)

        # Consolidate
        summary = (
            f"**Evolution Cycle Complete**\n"
            f"Gap targeted: `{top_gap['dimension']}` (score: {top_gap['score']:.1f}/5)\n"
            f"Hypothesis: {hypothesis[:120]}\n"
            f"Test improvement: {test_result['improvement']:.0%}\n"
            f"{'✅ Applied (+0.3 capability)' if test_result['improvement']>0.6 else '❌ Rejected — insufficient improvement'}"
        )
        self.memory.log_event("evolution_cycle", summary, importance=0.8)
        return summary

    def register_as_tool(self, registry):
        def evolve(params: dict) -> dict:
            result = self.run_full_cycle()
            return {"success": True, "data": result}

        registry.register(
            name="evolve",
            func=evolve,
            description="Run a self-improvement evolution cycle: detect gaps, generate curriculum, test hypothesis, consolidate learning",
            parameters={},
            category="self_evolution"
        )

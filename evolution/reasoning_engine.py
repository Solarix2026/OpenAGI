# Copyright (c) 2026 ApeironAI
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""
reasoning_engine.py — Structured logical reasoning

Chain-of-Thought (CoT) and Tree-of-Thought (ToT) for complex reasoning.
Different from innovation_engine (creative/novelty).
This is for: logic, analysis, decisions, debugging.
"""
import re
import json
import logging
from core.llm_gateway import call_nvidia

log = logging.getLogger("Reasoning")


class ReasoningEngine:
    def chain_of_thought(self, problem: str, depth: int = 3) -> dict:
        """Explicit step-by-step reasoning. Forces NVIDIA to show work."""
        prompt = f"""Reason through this problem step by step.
Problem: {problem}

Format:
STEP 1 — [what you're analyzing]: [reasoning]
STEP 2 — [what you're analyzing]: [reasoning]
...
CONCLUSION: [final answer based on steps]
CONFIDENCE: [0-100]%
ASSUMPTIONS: [list any assumptions made]

Be rigorous. Show logical steps. Identify missing evidence."""

        raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=800)

        conclusion = ""
        m = re.search(r"CONCLUSION:\s*(.+?)(?:CONFIDENCE:|$)", raw, re.DOTALL)
        if m:
            conclusion = m.group(1).strip()

        confidence = 70
        m = re.search(r"CONFIDENCE:\s*(\d+)", raw)
        if m:
            confidence = int(m.group(1))

        return {
            "success": True,
            "reasoning": raw,
            "conclusion": conclusion,
            "confidence": confidence,
            "problem": problem
        }

    def tree_of_thought(self, problem: str, branches: int = 3) -> dict:
        """Explore multiple reasoning paths. Good for decisions/strategy."""
        branch_prompt = f"""For this problem, generate {branches} DIFFERENT approaches:
"{problem}"

For each, describe in 2-3 sentences how to attack the problem differently.

Return JSON: {{"approaches": [{{"id": 1, "approach": "...", "strength": "...", "weakness": "..."}}]}}"""

        raw = call_nvidia([{"role": "user", "content": branch_prompt}], max_tokens=500)
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        branches_data = json.loads(m.group(0)).get("approaches", []) if m else []

        eval_prompt = f"""Problem: "{problem}"
Approaches: {json.dumps(branches_data, ensure_ascii=False)}

Which approach is strongest? Apply it to solve fully.

Return JSON: {{"best_approach": 1, "reasoning": "...", "solution": "...", "trade_offs": "..."}}"""

        raw2 = call_nvidia([{"role": "user", "content": eval_prompt}], max_tokens=600)
        m2 = re.search(r'\{.*\}', raw2, re.DOTALL)
        result = json.loads(m2.group(0)) if m2 else {}

        return {
            "success": True,
            "approaches_explored": len(branches_data),
            "best_approach": result.get("best_approach"),
            "solution": result.get("solution", ""),
            "trade_offs": result.get("trade_offs", ""),
            "all_approaches": branches_data
        }

    def steelman_debate(self, proposition: str) -> dict:
        """Steelman both sides of a proposition."""
        prompt = f"""Steelman both sides of: "{proposition}"

FOR (strongest case for):
1. [strongest argument]
2. [evidence]
3. [real-world example]

AGAINST (strongest objections):
1. [strongest objection]
2. [counter-evidence]
3. [risk/failure mode]

SYNTHESIS: [balanced conclusion]
RECOMMENDATION: [actionable decision]"""

        raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=700)

        rec = ""
        m = re.search(r"RECOMMENDATION:\s*(.+?)$", raw, re.DOTALL)
        if m:
            rec = m.group(1).strip()

        return {
            "success": True,
            "analysis": raw,
            "recommendation": rec,
            "proposition": proposition
        }

    def debug_logic(self, problem: str) -> dict:
        """Find logical errors in an argument or code."""
        prompt = f"""Analyze this for logical errors:
{problem}

Check for:
1. False premises
2. Invalid inferences
3. Missing steps
4. Circular reasoning
5. Scope creep

For each error: location, type, fix.

Return JSON: {{"errors": [{{"location": "...", "type": "...", "fix": "..."}}], "severity": "...", "fixed_version": "..."}}"""

        raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=700)
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        result = json.loads(m.group(0)) if m else {"errors": [], "severity": "unknown"}

        return {"success": True, **result, "input": problem[:200]}

    def register_as_tool(self, registry):
        engine = self

        def reason(params: dict) -> dict:
            mode = params.get("mode", "cot")
            problem = params.get("problem", "")
            if mode == "tree":
                return engine.tree_of_thought(problem)
            elif mode == "debate":
                return engine.steelman_debate(problem)
            elif mode == "debug":
                return engine.debug_logic(problem)
            return engine.chain_of_thought(problem)

        registry.register(
            "reason",
            reason,
            "Structured logical reasoning: chain-of-thought (cot), tree-of-thought (tree), "
            "steelman debate (debate), or error detection (debug)",
            {"problem": {"type": "string", "required": True}, "mode": {"type": "string", "default": "cot"}},
            "reasoning"
        )

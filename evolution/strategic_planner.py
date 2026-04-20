# Copyright (c) 2026 Solarix2026
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""
strategic_planner.py — Multi-step plan generation and execution

Converts a high-level goal into an ordered sequence of tool calls.
Evaluates plan quality before execution. Supports rollback.

Different from DAGWorkflow (which is parallel). This is sequential
planning with dependency tracking and mid-plan replanning when steps fail.
"""
import json
import re
import logging
from core.llm_gateway import call_nvidia

log = logging.getLogger("Planner")


class StrategicPlanner:
    def __init__(self, memory, executor):
        self.memory = memory
        self.executor = executor

    def plan_autonomously(self, goal: str, constraints: list = None) -> list[dict]:
        """
        Generate ordered plan to achieve goal.
        Returns: [{"step": 1, "tool": "websearch", "params": {...}, "rationale": "..."}]
        """
        available_tools = self.executor.registry.list_tools()
        prompt = f"""Create a step-by-step plan to achieve: "{goal}"

Constraints: {constraints or "none"}

Available tools: {available_tools}

Return JSON: {{"plan": [{{"step": 1, "tool": "tool_name", "params": {{}}, "rationale": "why this step", "expected_output": "what this produces"}}], "success_criteria": "how to know the goal is achieved", "risk": "main failure point"}}"""
        raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=1000)
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        result = json.loads(m.group(0)) if m else {"plan": []}
        self.memory.log_event("plan_generated", goal, {"steps": len(result.get("plan", []))}, importance=0.7)
        return result.get("plan", [])

    def execute_plan(self, plan: list[dict], notify_fn=None) -> dict:
        """Execute plan step by step. Replan on failure."""
        results = []
        for step in plan:
            tool = step.get("tool")
            params = step.get("params", {})
            log.info(f"[PLAN] Step {step.get('step')}: {tool}")
            if notify_fn:
                notify_fn(f"🔄 Step {step.get('step')}: {step.get('rationale', '')[:50]}")

            result = self.executor.execute({"action": tool, "parameters": params})
            results.append({"step": step.get("step"), "tool": tool, "success": result.get("success"), "result": result})

            if not result.get("success"):
                log.warning(f"[PLAN] Step {step.get('step')} failed: {result.get('error')}")
                # Replan remaining steps
                remaining = self.replan_after_failure(step, result.get("error", ""), plan)
                if remaining:
                    results += self.execute_plan(remaining, notify_fn).get("steps", [])
                break

        return {"steps": results, "completed": sum(1 for r in results if r.get("success"))}

    def replan_after_failure(self, failed_step: dict, error: str, original_plan: list) -> list[dict]:
        """Generate alternative steps after a failure."""
        prompt = f"""Step {failed_step.get('step')} failed: {failed_step.get('tool')}

Error: {error}

Original goal: continue the plan with these remaining steps: {original_plan[failed_step.get('step', 0):]}

Generate alternative steps to still achieve the goal.

Return JSON: {{"alternative_steps": [{{"step": "...", "tool": "...", "params": {{}}, "rationale": "..."}}]}}"""
        raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=600)
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        result = json.loads(m.group(0)) if m else {}
        return result.get("alternative_steps", [])

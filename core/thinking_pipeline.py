# Copyright (c) 2026 ApeironAI
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""
thinking_pipeline.py — Multi-layer thinking pipeline for complex tasks.

Layer 0 (Groq 8B, ~100ms): Intent + complexity score
Layer 1 (Kimi fast, ~300ms): Decompose → sub-goals
Layer 2 (Kimi full, ~800ms): Execute plan with reflection
Layer 3 (optional, ~500ms): Self-critique + refine output

Triggered when complexity_score > 0.6 from Layer 0.
Simple queries (hello, open calc) bypass all layers → direct response.
"""
import re, json, logging, time
from core.llm_gateway import call_groq_router, call_nvidia

log = logging.getLogger("ThinkingPipeline")


class ThinkingPipeline:
    def __init__(self, memory=None):
        self.memory = memory
        self._layer_times = {}

    def assess_complexity(self, user_input: str) -> dict:
        """Layer 0: Groq 8B, fast complexity scoring.
        Returns complexity 0-1 and task_type.
        """
        prompt = f"""Assess task complexity for an AI agent. Return JSON only.
Task: "{user_input}"
Return: {{"complexity": 0.0-1.0, "task_type": "simple|research|automation|creative|reasoning|planning", "requires_steps": true/false, "estimated_tool_calls": 0-10, "needs_computer_control": true/false}}
Complexity guide:
- 0.0-0.3: single tool or conversation (hello, open calc, what time)
- 0.3-0.6: 2-3 tools, some reasoning (summarize news + save to file)
- 0.6-0.8: multi-step plan, browser/computer use (research + write report)
- 0.8-1.0: complex automation (book flight, fill form, cross-app workflow)"""
        try:
            raw = call_groq_router([{"role": "user", "content": prompt}], max_tokens=150)
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                return json.loads(m.group(0))
        except Exception as e:
            log.debug(f"Layer 0 failed: {e}")
        return {"complexity": 0.3, "task_type": "simple", "requires_steps": False}

    def decompose_task(self, user_input: str, complexity_data: dict) -> dict:
        """Layer 1: Kimi fast, decompose into sub-goals. Only called if complexity > 0.6."""
        prompt = f"""Decompose this complex task into ordered sub-goals.
Task: "{user_input}"
Task type: {complexity_data.get('task_type')}
Estimated steps: {complexity_data.get('estimated_tool_calls', 3)}
Return JSON: {{
  "goal": "main objective",
  "sub_goals": [
    {{"step": 1, "goal": "...", "tool_hint": "tool_name or null", "depends_on": []}},
    ...
  ],
  "success_criteria": "how to verify completion",
  "abort_conditions": ["condition that means we should stop"],
  "human_approval_needed": true/false
}}"""
        try:
            raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=600, fast=True)
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                return json.loads(m.group(0))
        except Exception as e:
            log.debug(f"Layer 1 failed: {e}")
        return {"goal": user_input, "sub_goals": [], "human_approval_needed": False}

    def self_critique(self, original_task: str, response: str) -> str:
        """Layer 3: Self-critique — only for complex tasks where quality matters."""
        prompt = f"""Review this AI response for quality and completeness.
Original task: "{original_task}"
Response given: "{response[:800]}"
Check: 1. Did it fully address the task? 2. Any factual errors or hallucinations? 3. Missing important steps?
If the response is good (score >= 8/10), return exactly: PASS
If improvements needed, return the improved version directly (no preamble):"""
        try:
            result = call_nvidia([{"role": "user", "content": prompt}], max_tokens=600, fast=True)
            result = (result or "").strip()
            if result and result != "PASS" and len(result) > 50:
                log.info("[THINKING] Layer 3 refined response")
                return result
        except Exception as e:
            log.debug(f"Layer 3 failed: {e}")
        return response

    def should_ask_approval(self, decomposition: dict) -> tuple[bool, str]:
        """Check if task needs human approval before execution."""
        if not decomposition.get("human_approval_needed"):
            return False, ""
        sub_goals = decomposition.get("sub_goals", [])
        irreversible = [s for s in sub_goals if any(
            word in s.get("goal", "").lower()
            for word in ["book", "purchase", "buy", "pay", "submit", "send email", "delete", "transfer"]
        )]
        if irreversible:
            steps_str = "\n".join(f"  {i+1}. {s['goal']}" for i, s in enumerate(irreversible))
            return True, f"This will perform irreversible actions:\n{steps_str}\n\nConfirm? (yes/no)"
        return False, ""

    def run(self, user_input: str, execute_fn, simple_response_fn) -> tuple[str, dict]:
        """Main pipeline entry point. Returns (response, metadata)"""
        t0 = time.time()
        meta = {"layers_used": [], "total_ms": 0}

        # Layer 0: Complexity assessment (always runs, ~100ms)
        complexity = self.assess_complexity(user_input)
        meta["layers_used"].append("L0_complexity")
        meta["complexity"] = complexity.get("complexity", 0.3)
        score = complexity.get("complexity", 0.3)

        # Simple path: bypass all layers
        if score < 0.4:
            response = simple_response_fn(user_input)
            meta["path"] = "simple"
            meta["total_ms"] = int((time.time() - t0) * 1000)
            return response, meta

        # Layer 1: Decompose (complexity >= 0.4)
        if score >= 0.4:
            decomposition = self.decompose_task(user_input, complexity)
            meta["layers_used"].append("L1_decompose")
            meta["sub_goals"] = len(decomposition.get("sub_goals", []))

            # Check if approval needed
            needs_approval, approval_msg = self.should_ask_approval(decomposition)
            if needs_approval:
                meta["path"] = "pending_approval"
                meta["decomposition"] = decomposition
                return approval_msg, meta

        # Layer 2: Execute
        response = execute_fn(user_input, decomposition if score >= 0.4 else None)
        meta["layers_used"].append("L2_execute")

        # Layer 3: Self-critique (only for high complexity)
        if score >= 0.7 and response and len(response) > 100:
            response = self.self_critique(user_input, response)
            meta["layers_used"].append("L3_critique")

        meta["path"] = "complex"
        meta["total_ms"] = int((time.time() - t0) * 1000)
        log.info(f"[THINKING] {meta['layers_used']} | {meta['total_ms']}ms | complexity={score:.2f}")
        return response, meta

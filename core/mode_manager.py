# Copyright (c) 2026 ApeironAI
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""
mode_manager.py — Intelligent mode switching

Modes: AUTO — default, kernel decides based on task
       CODE — GitHub Spark-style app builder (TypeScript/React/FastAPI)
       REASON — Extended reasoning with explicit CoT steps (Kimi k2.5 thinking)
       PLAN — Multi-step planning for complex goals before execution
       RESEARCH — Deep research with web search + synthesis

Auto-switching rules:
User asks to build app / "create X app" / "SaaS" → CODE mode
User asks complex analysis / "why" / "explain deeply" → REASON mode
User asks multi-step goal / "help me achieve X" → PLAN mode
Long task detected (estimated > 3 steps) → PLAN mode first

Each mode changes:
- NVIDIA temperature (CODE: 0.2, REASON: 0.5, PLAN: 0.6, AUTO: 0.7)
- System prompt additions
- Whether reasoning chain is shown
- Max tokens (REASON: 2000, CODE: 3000, PLAN: 1500)
"""
import re, logging
from enum import Enum

log = logging.getLogger("ModeManager")


class Mode(Enum):
    AUTO = "auto"
    CODE = "code"      # GitHub Spark: NL → working app
    REASON = "reason"  # Extended CoT, show reasoning steps
    PLAN = "plan"      # Plan first, then execute
    RESEARCH = "research"  # Web search + synthesis


MODE_SYSTEM_PROMPTS = {
    Mode.CODE: """ ## CODE MODE ACTIVE
You are an expert full-stack developer. Generate complete, production-ready code.
- Stack: TypeScript + React (frontend), FastAPI/Python (backend)
- Always generate working code, never placeholders
- Include error handling, types, and basic tests
- Structure: one file per component, clean imports
- After generating: suggest deployment steps
""",
    Mode.REASON: """ ## EXTENDED REASONING MODE ACTIVE
Think step by step. Show your reasoning explicitly.
Format each response as:
THINKING: [your reasoning process, explore alternatives, consider edge cases]
ANSWER: [final conclusion based on the thinking]
Be thorough. Challenge your own assumptions. Consider what could be wrong.
""",
    Mode.PLAN: """ ## PLANNING MODE ACTIVE
Before executing ANY task, create a plan first.
Format:
GOAL: [what we're trying to achieve]
ANALYSIS: [what information do we have, what's missing]
PLAN:
Step 1: [specific action] → [expected outcome]
Step 2: ...
RISKS: [what could go wrong]
PROCEED? [ask user to confirm before executing]
""",
    Mode.RESEARCH: """ ## RESEARCH MODE ACTIVE
Conduct thorough research before answering.
1. Search for recent information
2. Cross-reference multiple sources
3. Synthesize findings, note contradictions
4. Cite sources and note publication dates
5. Separate facts from interpretations
""",
}


MODE_CONFIGS = {
    Mode.AUTO: {"temperature": 0.7, "max_tokens": 1200, "fast": False},
    Mode.CODE: {"temperature": 0.2, "max_tokens": 3000, "fast": False},
    Mode.REASON: {"temperature": 0.5, "max_tokens": 2000, "fast": False},
    Mode.PLAN: {"temperature": 0.6, "max_tokens": 1500, "fast": False},
    Mode.RESEARCH: {"temperature": 0.5, "max_tokens": 1500, "fast": False},
}


class ModeManager:
    def __init__(self):
        self._current = Mode.AUTO
        self._user_override = False  # True if user explicitly set mode

    @property
    def current(self) -> Mode:
        return self._current

    def set_mode(self, mode_str: str) -> str:
        """Set mode from user command. Returns confirmation string."""
        mode_map = {
            "auto": Mode.AUTO,
            "code": Mode.CODE,
            "coding": Mode.CODE,
            "reason": Mode.REASON,
            "reasoning": Mode.REASON,
            "think": Mode.REASON,
            "plan": Mode.PLAN,
            "planning": Mode.PLAN,
            "research": Mode.RESEARCH,
        }
        m = mode_map.get(mode_str.lower())
        if m:
            self._current = m
            self._user_override = True
            return f"Mode: **{m.value.upper()}**"
        return f"Unknown mode. Available: {list(mode_map.keys())}"

    def auto_detect(self, user_input: str) -> Mode:
        """
        Auto-detect best mode for this input.
        Only switches if user hasn't explicitly set a mode.
        """
        if self._user_override:
            return self._current  # Respect user choice

        text = user_input.lower()

        # CODE triggers
        if any(w in text for w in [
            "build an app", "create app", "build a saas", "generate app",
            "create website", "build website", "write code for",
            "typescript", "react component", "fastapi", "nextjs",
            "build me a", "make me a", "create a tool that"
        ]):
            return Mode.CODE

        # REASON triggers
        if any(w in text for w in [
            "why does", "explain deeply", "analyze", "critique",
            "what are the implications", "think through", "is it true that",
            "prove", "disprove", "steelman", "complex", "nuanced"
        ]):
            return Mode.REASON

        # PLAN triggers (long/multi-step tasks)
        if any(w in text for w in [
            "help me achieve", "how do i", "plan for", "strategy for",
            "roadmap", "step by step", "i want to", "help me build my", "launch"
        ]):
            return Mode.PLAN

        # RESEARCH triggers
        if any(w in text for w in [
            "research", "find out", "what is the latest", "news about",
            "current state of", "compare"
        ]):
            return Mode.RESEARCH

        return Mode.AUTO

    def get_config(self, mode: Mode = None) -> dict:
        return MODE_CONFIGS.get(mode or self._current, MODE_CONFIGS[Mode.AUTO])

    def get_system_prompt_addition(self, mode: Mode = None) -> str:
        return MODE_SYSTEM_PROMPTS.get(mode or self._current, "")

    def reset_to_auto(self):
        """Reset after long-form response (e.g., code was generated)."""
        if not self._user_override:
            self._current = Mode.AUTO

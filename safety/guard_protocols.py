# Copyright (c) 2026 HackerTMJ (门牌号3号)
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/HackerTMJ/OpenAGI

"""
guard_protocols.py — Safety protocols for autonomous operations

Three protocols:
1. Telos Anchor: reject any action that contradicts system Telos
2. Tripartite Shield: every self-modification checked by 3 criteria
   (safety, alignment, capability preservation)
3. Hermetic Sandbox: tool invention code exec in isolated namespace,
   cannot access kernel state directly

is_safe(action, params) → bool
Used by ProactiveEngine before auto-execution.
"""
import logging
import re

log = logging.getLogger("Guard")


class GuardProtocols:
    def __init__(self, memory):
        self.memory = memory
        self._telos = self._load_telos()

    def _load_telos(self) -> str:
        """Load system telos from memory."""
        try:
            meta = self.memory.get_meta_knowledge("telos")
            if meta and meta.get("content"):
                return str(meta["content"])
        except Exception:
            pass
        return "Expand autonomous capability: understand more, act more precisely, evolve continuously without human prompting."

    def _check_telos_anchor(self, action: str, params: dict) -> bool:
        """
        Protocol 1: Telos Anchor
        Reject actions that contradict the system's core mission.
        """
        dangerous_patterns = [
            "delete.*kernel", "remove.*core", "modify.*telos", "disable.*guard",
            "bypass.*safety", "corrupt.*memory", "reset.*evolution"
        ]
        combined = f"{action} {str(params).lower()}"
        for pattern in dangerous_patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                log.warning(f"[GUARD] Telos anchor violated: {pattern}")
                return False
        return True

    def _check_tripartite_shield(self, action: str, params: dict) -> tuple[bool, str]:
        """
        Protocol 2: Tripartite Shield
        Every self-modification must pass:
        - Safety: cannot harm user or system integrity
        - Alignment: must align with telos
        - Capability preservation: must not reduce core capabilities
        """
        # Safety check
        dangerous_actions = ["delete", "remove", "wipe", "format", "uninstall"]
        if action.lower() in dangerous_actions:
            # Check for protected resources
            params_str = str(params)
            protected = ["memory", "kernel", "core", "workspace/agent_state.db"]
            if any(p in params_str for p in protected):
                return False, "Safety: protected resource"

        # Alignment check
        if not self._check_telos_anchor(action, params):
            return False, "Alignment: violates telos"

        # Capability preservation
        if action.lower() in ["disable", "deactivate"]:
            core_modules = ["will", "evolution", "guard", "memory"]
            params_str = str(params)
            if any(m in params_str for m in core_modules):
                return False, "Capability: core module protection"

        return True, "passed"

    def _check_hermetic_sandbox(self, code: str) -> bool:
        """
        Protocol 3: Hermetic Sandbox
        Code executed in tool invention must be isolated.
        """
        forbidden_patterns = [
            "__import__", "import os", "import sys", "subprocess.",
            "eval(", "exec(", "compile(", "__file__", "__name__ == '__main__'",
            "globals(", "locals(", "dir(", "class.*Kernel", "def.*kernel",
            "memory", "AgentMemory", "ToolRegistry"
        ]
        for pattern in forbidden_patterns:
            if pattern in code:
                log.warning(f"[GUARD] Hermetic sandbox violation: {pattern}")
                return False
        return True

    def is_safe(self, action: str, params: dict = None, is_self_modification: bool = False) -> bool:
        """
        Main safety check. Returns True if action is permitted.
        """
        params = params or {}

        # Always check telos anchor
        if not self._check_telos_anchor(action, params):
            return False

        # Stricter checks for self-modification
        if is_self_modification:
            safe, reason = self._check_tripartite_shield(action, params)
            if not safe:
                log.warning(f"[GUARD] Tripartite shield blocked: {reason}")
                return False

        # If params contain code, check sandbox
        for val in params.values():
            if isinstance(val, str) and len(val) > 100:
                if not self._check_hermetic_sandbox(val):
                    return False

        return True

    def validate_evolution(self, hypothesis: str) -> bool:
        """Validate if an evolution hypothesis is safe to test."""
        dangerous = ["delete", "wipe", "disable", "bypass", "corrupt", "modify.*source"]
        for d in dangerous:
            if re.search(d, hypothesis, re.IGNORECASE):
                log.warning(f"[GUARD] Evolution hypothesis blocked: {d}")
                return False
        return True

    def validate_invention(self, code: str) -> tuple[bool, str]:
        """Validate invented tool code before execution."""
        if not self._check_hermetic_sandbox(code):
            return False, "Code violates sandbox restrictions"

        # Additional checks
        if "import" in code and "os" in code:
            # Allow but log
            log.info("[GUARD] Tool invention imports os module")

        return True, "passed"

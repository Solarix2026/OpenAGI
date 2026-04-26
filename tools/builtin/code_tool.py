# tools/builtin/code_tool.py
"""Autonomous code execution and repair loop.

This is the MetacognitiveEngine + Refinement Loop from the SMGI framework.

Loop contract:
1. Write code to temp file
2. Execute in REPL sandbox
3. SUCCESS → return result immediately
4. ModuleNotFoundError → pip install missing dep → retry (no LLM needed)
5. Other error → extract exact line/traceback → LLM surgical repair (str_replace only) → retry
6. Max attempts exhausted → return failure with full repair_history for diagnostics

NEVER rewrites entire file to fix a bug. Always str_replace on the exact failing line.
This is the architectural invariant: surgical repair, not wholesale replacement.
"""
from __future__ import annotations

import json
import re
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import structlog

from gateway.llm_gateway import LLMGateway, LLMRequest
from sandbox.repl import PythonREPL, REPLResult
from tools.base_tool import BaseTool, ToolMeta, ToolResult

logger = structlog.get_logger()


@dataclass
class RepairAttempt:
    """Record of one repair attempt — full audit trail."""
    attempt_number: int
    error_type: str
    error_message: str
    action: str  # "install_dep" | "str_replace" | "full_rewrite_fallback"
    old_str: str = ""
    new_str: str = ""
    dep_installed: str = ""
    success: bool = False


@dataclass
class CodeResult:
    """Result of execute_with_repair."""
    success: bool
    output: str = ""
    error: str = ""
    final_code: str = ""
    attempts: int = 0
    repair_history: list[RepairAttempt] = field(default_factory=list)
    execution_time_ms: float = 0.0


class CodeTool(BaseTool):
    """
    The repair loop. Core of L2 capability.

    Usage:
        tool = CodeTool(repl=repl, llm=gateway, max_attempts=5)
        result = await tool.execute_with_repair(code)
    """

    def __init__(
        self,
        repl: Optional[PythonREPL] = None,
        llm: Optional[LLMGateway] = None,
        max_attempts: int = 5,
    ) -> None:
        self.repl = repl or PythonREPL()
        self.llm = llm
        self.max_attempts = max_attempts

    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="code",
            description=(
                "Write and execute Python code. Autonomously repairs errors: "
                "installs missing packages, applies surgical line-level fixes. "
                "Returns output, error trace, and full repair history."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to execute"},
                    "max_attempts": {"type": "integer", "default": 5},
                    "install_deps": {"type": "boolean", "default": True},
                },
                "required": ["code"],
            },
            risk_score=0.5,
            categories=["code", "execution"],
        )

    async def execute(self, code: str, max_attempts: int = 5, install_deps: bool = True, **kwargs) -> ToolResult:
        result = await self.execute_with_repair(code, max_attempts=max_attempts, install_deps=install_deps)
        return ToolResult(
            success=result.success,
            tool_name="code",
            data={
                "output": result.output,
                "final_code": result.final_code,
                "attempts": result.attempts,
                "repair_history": [r.__dict__ for r in result.repair_history],
            },
            error=result.error,
            execution_time_ms=result.execution_time_ms,
        )

    async def execute_with_repair(
        self,
        code: str,
        max_attempts: int = None,
        install_deps: bool = True,
    ) -> CodeResult:
        max_att = max_attempts or self.max_attempts
        current_code = code
        repair_history: list[RepairAttempt] = []
        start = time.time()

        for attempt in range(1, max_att + 1):
            logger.info("code.repair.attempt", attempt=attempt, max=max_att)

            repl_result: REPLResult = await self.repl.execute(current_code)

            if repl_result.success:
                return CodeResult(
                    success=True,
                    output=repl_result.output,
                    final_code=current_code,
                    attempts=attempt,
                    repair_history=repair_history,
                    execution_time_ms=(time.time() - start) * 1000,
                )

            # ── Repair Decision Tree ──────────────────────────────────────────
            error_type = repl_result.error_type or "UnknownError"
            error_msg = repl_result.error

            logger.warning("code.repair.error", attempt=attempt, error_type=error_type)

            # Path 1: Missing dependency — no LLM needed
            if repl_result.missing_modules and install_deps:
                for module in repl_result.missing_modules:
                    pkg = self._module_to_package(module)
                    logger.info("code.repair.installing", package=pkg)
                    install_result = await self.repl.install_package(pkg)

                    repair = RepairAttempt(
                        attempt_number=attempt,
                        error_type="ModuleNotFoundError",
                        error_message=error_msg,
                        action="install_dep",
                        dep_installed=pkg,
                        success=install_result.success,
                    )
                    repair_history.append(repair)

                    if not install_result.success:
                        logger.error("code.repair.install_failed", pkg=pkg)
                continue  # Retry with same code after install

            # Path 2: Code error — LLM surgical repair
            if self.llm is None:
                break  # No LLM available, give up

            repair_instruction = await self._get_surgical_repair(current_code, error_type, error_msg)

            if repair_instruction is None:
                logger.warning("code.repair.llm_gave_no_fix", attempt=attempt)
                break

            action = repair_instruction.get("action", "str_replace")
            old_str = repair_instruction.get("old_str", "")
            new_str = repair_instruction.get("new_str", "")

            repair = RepairAttempt(
                attempt_number=attempt,
                error_type=error_type,
                error_message=error_msg,
                action=action,
                old_str=old_str,
                new_str=new_str,
            )

            if action == "str_replace" and old_str and old_str in current_code:
                current_code = current_code.replace(old_str, new_str, 1)
                repair.success = True
                logger.info("code.repair.str_replace_applied", old=old_str[:50])
            elif action == "full_rewrite":
                # Last resort — only if str_replace impossible
                rewritten = repair_instruction.get("code", "")
                if rewritten:
                    current_code = rewritten
                    repair.success = True
                    logger.warning("code.repair.full_rewrite_used")
            else:
                logger.warning("code.repair.old_str_not_found", old_str=old_str[:50])

            repair_history.append(repair)

        # All attempts exhausted
        return CodeResult(
            success=False,
            error=f"Repair failed after {max_att} attempts. Last error: {repl_result.error}",
            final_code=current_code,
            attempts=max_att,
            repair_history=repair_history,
            execution_time_ms=(time.time() - start) * 1000,
        )

    async def _get_surgical_repair(
        self,
        code: str,
        error_type: str,
        error_msg: str,
    ) -> Optional[dict]:
        """Ask LLM for a surgical repair instruction.

        Returns a dict with action: str_replace + old_str + new_str,
        or action: full_rewrite + code as last resort.
        Never returns vague advice — always returns machine-actionable patch.
        """
        if self.llm is None:
            return None

        # Extract line number from traceback if available
        line_context = self._extract_error_context(code, error_msg)

        prompt = f"""You are a code repair engine. Given a Python error, return ONLY a JSON repair instruction.

ERROR TYPE: {error_type}
ERROR MESSAGE:
{error_msg}

FAILING CODE:
```python
{code}
```

ERROR CONTEXT (lines around error):
{line_context}

Return EXACTLY this JSON format (no markdown, no explanation):
{{
  "action": "str_replace",
  "old_str": "<exact string to replace — must exist verbatim in code>",
  "new_str": "<fixed replacement>",
  "reasoning": "<one line>"
}}

If str_replace is impossible (structural rewrite needed):
{{
  "action": "full_rewrite",
  "code": "<complete corrected code>",
  "reasoning": "<one line>"
}}

Rules:
- old_str must appear EXACTLY ONCE in the code
- Fix ONLY the error — do not refactor or improve unrelated code
- If the fix requires an import, add it at the top via str_replace on existing imports"""

        from gateway.llm_gateway import LLMRequest
        response = await self.llm.complete(LLMRequest(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.0,  # Deterministic for code repair
        ))

        try:
            raw = response.content.strip()
            # Strip markdown fences if present
            raw = re.sub(r"^```json?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("code.repair.json_parse_failed", raw=response.content[:200])
            return None

    def _extract_error_context(self, code: str, error_msg: str, context_lines: int = 3) -> str:
        """Extract lines around the error line number from traceback."""
        lines = code.splitlines()
        match = re.search(r"line (\d+)", error_msg)
        if not match:
            return code[:500]  # Return first 500 chars if no line number

        line_num = int(match.group(1)) - 1
        start = max(0, line_num - context_lines)
        end = min(len(lines), line_num + context_lines + 1)

        context = []
        for i, line in enumerate(lines[start:end], start=start + 1):
            marker = ">>>" if i == line_num + 1 else "   "
            context.append(f"{marker} {i:3d}: {line}")
        return "\n".join(context)

    def _module_to_package(self, module: str) -> str:
        """Map import name to pip package name for common mismatches."""
        mappings = {
            "cv2": "opencv-python",
            "PIL": "Pillow",
            "sklearn": "scikit-learn",
            "bs4": "beautifulsoup4",
            "yaml": "pyyaml",
            "dotenv": "python-dotenv",
            "faiss": "faiss-cpu",
        }
        return mappings.get(module, module)

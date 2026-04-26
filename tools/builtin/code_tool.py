# tools/builtin/code_tool.py
"""Code execution and repair tool.

Executes code in sandbox and attempts repairs on failures.
"""
from typing import Any

import structlog

from tools.base_tool import BaseTool, ToolMeta, ToolResult
from sandbox.repl import PythonREPL, REPLStatus
from config.settings import get_settings

logger = structlog.get_logger()


class CodeTool(BaseTool):
    """
    Execute and repair code in sandbox.

    - Executes code in isolated REPL
    - Detects errors and missing modules
    - Attempts automatic repairs
    - Uses surgical str_replace (not full rewrite)
    """

    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="code",
            description="Execute code in sandbox and attempt repairs on failures",
            parameters={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute"
                    },
                    "max_repair_attempts": {
                        "type": "integer",
                        "description": "Maximum repair attempts (default: from config)",
                        "default": None
                    }
                },
                "required": ["code"]
            },
            risk_score=0.8,  # Code execution is high risk
            categories=["code", "execution", "repair"],
            examples=[
                {
                    "code": "print('Hello, world!')",
                    "description": "Simple print statement"
                }
            ]
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Execute code with repair loop."""
        import time
        start_time = time.time()

        code = kwargs.get("code", "")
        max_repair_attempts = kwargs.get("max_repair_attempts")

        if not code:
            return ToolResult(
                success=False,
                tool_name=self.meta.name,
                error="No code provided"
            )

        # Get max attempts from config if not specified
        if max_repair_attempts is None:
            config = get_settings()
            max_repair_attempts = config.max_code_repair_attempts

        repl = PythonREPL()
        repair_history = []

        try:
            # Initial execution
            result = await repl.execute(code)

            if result.success:
                return ToolResult(
                    success=True,
                    tool_name=self.meta.name,
                    data=result.output,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    metadata={"attempts": 0, "repairs": 0}
                )

            # Repair loop
            for attempt in range(max_repair_attempts):
                if result.status == REPLStatus.SUCCESS:
                    break

                repair_history.append({
                    "attempt": attempt + 1,
                    "error": result.error,
                    "error_type": result.error_type,
                    "missing_modules": result.missing_modules
                })

                # Attempt repair based on error type
                repaired_code = await self._attempt_repair(code, result)

                if repaired_code == code:
                    # No repair possible
                    break

                # Execute repaired code
                result = await repl.execute(repaired_code)

                if result.success:
                    return ToolResult(
                        success=True,
                        tool_name=self.meta.name,
                        data=result.output,
                        execution_time_ms=(time.time() - start_time) * 1000,
                        metadata={
                            "attempts": attempt + 1,
                            "repairs": attempt + 1,
                            "repair_history": repair_history
                        }
                    )

                # Update code for next iteration
                code = repaired_code

            # All repair attempts failed
            return ToolResult(
                success=False,
                tool_name=self.meta.name,
                error=f"Code execution failed after {max_repair_attempts} repair attempts",
                data=result.output,
                execution_time_ms=(time.time() - start_time) * 1000,
                metadata={
                    "attempts": max_repair_attempts,
                    "repairs": max_repair_attempts,
                    "repair_history": repair_history,
                    "final_error": result.error
                }
            )

        except Exception as e:
            logger.exception("code.tool.error", error=str(e))
            return ToolResult(
                success=False,
                tool_name=self.meta.name,
                error=f"Code execution failed: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )
        finally:
            await repl.close()

    async def _attempt_repair(self, code: str, result: Any) -> str:
        """Attempt to repair code based on error."""
        # Handle missing modules
        if result.missing_modules:
            for module in result.missing_modules:
                # Try to install the module
                repl = PythonREPL()
                try:
                    install_result = await repl.install_package(module)
                    if install_result.success:
                        logger.info("code.tool.installed_module", module=module)
                finally:
                    await repl.close()
            return code  # Return original code, module installation is external

        # Handle common syntax errors with surgical fixes
        if result.error_type == "SyntaxError":
            # Fix missing colons
            if "expected ':'" in result.error.lower():
                lines = code.split("\n")
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if (stripped.startswith(("def ", "class ", "if ", "elif ", "else:",
                                        "for ", "while ", "try:", "except", "finally:",
                                        "with ", "async ")) and
                        not stripped.endswith(":")):
                        lines[i] = line + ":"
                return "\n".join(lines)

            # Fix missing parentheses
            if "unexpected EOF" in result.error.lower():
                # Count parentheses and add missing ones
                open_parens = code.count("(")
                close_parens = code.count(")")
                if open_parens > close_parens:
                    return code + ")" * (open_parens - close_parens)

        # Handle indentation errors
        if result.error_type == "IndentationError":
            lines = code.split("\n")
            fixed_lines = []
            indent_level = 0

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    fixed_lines.append(line)
                    continue

                # Increase indent after colons
                if stripped.endswith(":"):
                    fixed_lines.append(line)
                    indent_level += 1
                # Decrease indent for dedent keywords
                elif stripped.startswith(("return", "break", "continue", "pass")):
                    indent_level = max(0, indent_level - 1)
                    fixed_lines.append("    " * indent_level + stripped)
                else:
                    fixed_lines.append("    " * indent_level + stripped)

            return "\n".join(fixed_lines)

        # No repair possible
        return code

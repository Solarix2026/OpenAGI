# tools/builtin/shell_tool.py
"""Shell command execution tool.

Executes shell commands in a controlled environment.
Uses subprocess for isolation and captures output.
"""
import asyncio
import subprocess
from typing import Any

import structlog

from tools.base_tool import BaseTool, ToolMeta, ToolResult

logger = structlog.get_logger()


class ShellTool(BaseTool):
    """
    Execute shell commands safely.

    - Uses subprocess for isolation
    - Captures stdout/stderr
    - Enforces timeouts
    - Returns exit codes
    """

    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="shell",
            description="Execute shell commands in a controlled environment",
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 30)",
                        "default": 30
                    },
                    "working_dir": {
                        "type": "string",
                        "description": "Working directory for command execution"
                    }
                },
                "required": ["command"]
            },
            risk_score=0.7,  # Shell commands are inherently risky
            categories=["system", "execution"],
            examples=[
                {
                    "command": "ls -la",
                    "description": "List files in current directory"
                },
                {
                    "command": "echo hello",
                    "description": "Print hello to stdout"
                }
            ]
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Execute a shell command."""
        import time
        start_time = time.time()

        command = kwargs.get("command", "")
        timeout = kwargs.get("timeout", 30)
        working_dir = kwargs.get("working_dir")

        if not command:
            return ToolResult(
                success=False,
                tool_name=self.meta.name,
                error="No command provided"
            )

        try:
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                shell=True
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

                return ToolResult(
                    success=False,
                    tool_name=self.meta.name,
                    error=f"Command timed out after {timeout}s",
                    execution_time_ms=(time.time() - start_time) * 1000,
                    metadata={"timeout": timeout}
                )

            # Decode output
            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")

            execution_time_ms = (time.time() - start_time) * 1000

            # Check exit code
            if process.returncode == 0:
                return ToolResult(
                    success=True,
                    tool_name=self.meta.name,
                    data=stdout_text,
                    execution_time_ms=execution_time_ms,
                    metadata={
                        "exit_code": process.returncode,
                        "stderr": stderr_text if stderr_text else None
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    tool_name=self.meta.name,
                    error=stderr_text or f"Command failed with exit code {process.returncode}",
                    data=stdout_text,
                    execution_time_ms=execution_time_ms,
                    metadata={
                        "exit_code": process.returncode,
                        "stderr": stderr_text
                    }
                )

        except Exception as e:
            logger.exception("shell.tool.error", command=command, error=str(e))
            return ToolResult(
                success=False,
                tool_name=self.meta.name,
                error=f"Shell execution failed: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )

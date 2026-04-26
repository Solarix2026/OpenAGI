# tools/builtin/file_tool.py
"""File system operations tool.

Read, write, list, and delete files safely.
"""
import os
from pathlib import Path
from typing import Any

import structlog

from tools.base_tool import BaseTool, ToolMeta, ToolResult

logger = structlog.get_logger()


class FileTool(BaseTool):
    """
    File system operations.

    - Read files
    - Write files
    - List directories
    - Delete files
    """

    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="file",
            description="Perform file system operations: read, write, list, delete",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["read", "write", "list", "delete"],
                        "description": "The action to perform"
                    },
                    "path": {
                        "type": "string",
                        "description": "File or directory path"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write (for write action)"
                    }
                },
                "required": ["action", "path"]
            },
            risk_score=0.6,
            categories=["filesystem", "io"],
            examples=[
                {
                    "action": "read",
                    "path": "/path/to/file.txt"
                },
                {
                    "action": "write",
                    "path": "/path/to/file.txt",
                    "content": "Hello, world!"
                }
            ]
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Execute file operation."""
        import time
        start_time = time.time()

        action = kwargs.get("action", "")
        path_str = kwargs.get("path", "")
        content = kwargs.get("content", "")

        if not action:
            return ToolResult(
                success=False,
                tool_name=self.meta.name,
                error="No action provided"
            )

        if not path_str:
            return ToolResult(
                success=False,
                tool_name=self.meta.name,
                error="No path provided"
            )

        path = Path(path_str)

        try:
            if action == "read":
                if not path.exists():
                    return ToolResult(
                        success=False,
                        tool_name=self.meta.name,
                        error=f"File not found: {path_str}"
                    )

                with open(path, "r", encoding="utf-8") as f:
                    file_content = f.read()

                return ToolResult(
                    success=True,
                    tool_name=self.meta.name,
                    data=file_content,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    metadata={"path": str(path), "size": len(file_content)}
                )

            elif action == "write":
                # Create parent directories if needed
                path.parent.mkdir(parents=True, exist_ok=True)

                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)

                return ToolResult(
                    success=True,
                    tool_name=self.meta.name,
                    data=f"Written {len(content)} bytes to {path_str}",
                    execution_time_ms=(time.time() - start_time) * 1000,
                    metadata={"path": str(path), "size": len(content)}
                )

            elif action == "list":
                if not path.exists():
                    return ToolResult(
                        success=False,
                        tool_name=self.meta.name,
                        error=f"Path not found: {path_str}"
                    )

                if path.is_file():
                    items = [str(path)]
                else:
                    items = [str(p) for p in path.iterdir()]

                return ToolResult(
                    success=True,
                    tool_name=self.meta.name,
                    data=items,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    metadata={"path": str(path), "count": len(items)}
                )

            elif action == "delete":
                if not path.exists():
                    return ToolResult(
                        success=False,
                        tool_name=self.meta.name,
                        error=f"Path not found: {path_str}"
                    )

                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    # For directories, remove recursively
                    import shutil
                    shutil.rmtree(path)

                return ToolResult(
                    success=True,
                    tool_name=self.meta.name,
                    data=f"Deleted: {path_str}",
                    execution_time_ms=(time.time() - start_time) * 1000,
                    metadata={"path": str(path)}
                )

            else:
                return ToolResult(
                    success=False,
                    tool_name=self.meta.name,
                    error=f"Unknown action: {action}"
                )

        except Exception as e:
            logger.exception("file.tool.error", action=action, path=path_str, error=str(e))
            return ToolResult(
                success=False,
                tool_name=self.meta.name,
                error=f"File operation failed: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )

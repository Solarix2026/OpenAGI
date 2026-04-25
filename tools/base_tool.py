"""Tool interface contract (ABC).

Every tool in OpenAGI extends BaseTool and implements:
- meta: Tool metadata for discovery
- execute: The actual tool logic (async)

Tools return typed ToolResult objects, never raw dicts.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator, Literal


@dataclass(frozen=True)
class ToolMeta:
    """Immutable metadata about a tool.

    This is what the registry searches over when agents
    query for capabilities.
    """
    name: str
    description: str
    parameters: dict[str, Any]
    risk_score: float = 0.0  # 0.0 (safe) to 1.0 (dangerous)
    categories: list[str] = field(default_factory=list)
    examples: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class ToolResult:
    """Typed result from tool execution.

    Never return raw dicts from tools. Always wrap in ToolResult.
    """
    success: bool
    tool_name: str
    data: Any = None
    error: str = ""
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolStreamChunk:
    """Chunk of streaming tool output."""
    chunk_type: Literal["stdout", "stderr", "progress", "result"]
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    """
    Abstract base class for all tools in OpenAGI.

    Tools are hot-swappable capabilities that extend the agent.
    They never hardcode their name or behavior — all configuration
    flows through meta and parameters.

    Example:
        class MyTool(BaseTool):
            @property
            def meta(self) -> ToolMeta:
                return ToolMeta(name="my_tool", ...)

            async def execute(self, **kwargs) -> ToolResult:
                # Tool logic here
                return ToolResult(success=True, ...)
    """

    @property
    @abstractmethod
    def meta(self) -> ToolMeta:
        """Return this tool's metadata."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with the given parameters.

        Must return a ToolResult. Never raise exceptions without
        catching and returning them in ToolResult.error.
        """
        pass

    async def execute_stream(self, **kwargs) -> AsyncIterator[ToolStreamChunk]:
        """Stream execution results. Default: yield final result."""
        result = await self.execute(**kwargs)
        yield ToolStreamChunk(
            chunk_type="result",
            content=str(result.data) if result.success else result.error,
            metadata={"success": result.success}
        )

    def validate_params(self, params: dict[str, Any]) -> tuple[bool, str]:
        """Validate parameters against schema.

        Override for custom validation. Default checks required fields.
        """
        schema = self.meta.parameters
        required = schema.get("required", [])

        missing = [k for k in required if k not in params]
        if missing:
            return False, f"Missing required parameters: {missing}"

        return True, ""


class ToolError(Exception):
    """Exception base for tool-specific errors."""
    def __init__(self, message: str, tool_name: str = ""):
        super().__init__(message)
        self.tool_name = tool_name

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
import structlog

logger = structlog.get_logger()


def convert_param_type(value: Any, param_type: str) -> Any:
    """Convert parameter value to the correct type.

    LLMs often pass parameters as strings when they should be other types.
    This function handles automatic type conversion.

    Args:
        value: The value to convert
        param_type: The target type ('string', 'integer', 'boolean', 'number')

    Returns:
        Converted value
    """
    if value is None:
        return None

    # If already the right type, return as-is
    if param_type == "string" and isinstance(value, str):
        return value
    if param_type == "integer" and isinstance(value, int):
        return value
    if param_type == "boolean" and isinstance(value, bool):
        return value
    if param_type == "number" and isinstance(value, (int, float)):
        return value

    # Convert to target type
    try:
        if param_type == "string":
            return str(value)
        elif param_type == "integer":
            if isinstance(value, str):
                return int(value.strip())
            return int(value)
        elif param_type == "boolean":
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            return bool(value)
        elif param_type == "number":
            if isinstance(value, str):
                return float(value.strip())
            return float(value)
    except (ValueError, TypeError):
        logger.warning("param_conversion_failed",
                      value=value,
                      target_type=param_type)
        return value  # Return original if conversion fails

    return value


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

    def convert_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Convert parameters to correct types based on schema.

        LLMs often pass parameters as strings. This function automatically
        converts them to the correct types based on the tool's parameter schema.
        """
        schema = self.meta.parameters
        properties = schema.get("properties", {})
        converted = {}

        for key, value in params.items():
            if key in properties:
                param_spec = properties[key]
                param_type = param_spec.get("type", "string")
                converted[key] = convert_param_type(value, param_type)
            else:
                # Keep unknown parameters as-is
                converted[key] = value

        return converted


class ToolError(Exception):
    """Exception base for tool-specific errors."""
    def __init__(self, message: str, tool_name: str = ""):
        super().__init__(message)
        self.tool_name = tool_name

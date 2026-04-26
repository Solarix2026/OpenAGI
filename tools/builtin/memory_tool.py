# tools/builtin/memory_tool.py
"""Memory operations tool.

Query and write to stratified memory.
"""
from typing import Any

import structlog

from tools.base_tool import BaseTool, ToolMeta, ToolResult
from memory.memory_core import MemoryCore, MemoryLayer

logger = structlog.get_logger()


class MemoryTool(BaseTool):
    """
    Interact with stratified memory.

    - Query memories across layers
    - Write new memories
    - Consolidate episodic to semantic
    """

    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="memory",
            description="Query and write to stratified memory (WORKING/EPISODIC/SEMANTIC/PROCEDURAL)",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["query", "write", "consolidate", "stats"],
                        "description": "Memory action to perform"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query (for query action)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to remember (for write action)"
                    },
                    "layer": {
                        "type": "string",
                        "enum": ["WORKING", "EPISODIC", "SEMANTIC", "PROCEDURAL"],
                        "description": "Memory layer (for write action)"
                    },
                    "layers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Layers to search (for query action)"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default: 5)",
                        "default": 5
                    }
                },
                "required": ["action"]
            },
            risk_score=0.2,
            categories=["memory", "storage"],
            examples=[
                {
                    "action": "query",
                    "query": "previous conversation",
                    "layers": ["EPISODIC", "SEMANTIC"]
                },
                {
                    "action": "write",
                    "content": "User prefers Python over JavaScript",
                    "layer": "EPISODIC"
                }
            ]
        )

    def __init__(self, memory_core: MemoryCore = None):
        super().__init__()
        self.memory_core = memory_core

    async def execute(self, **kwargs) -> ToolResult:
        """Execute memory operation."""
        import time
        start_time = time.time()

        action = kwargs.get("action", "")

        if not action:
            return ToolResult(
                success=False,
                tool_name=self.meta.name,
                error="No action provided"
            )

        if self.memory_core is None:
            return ToolResult(
                success=False,
                tool_name=self.meta.name,
                error="Memory core not initialized"
            )

        try:
            if action == "query":
                query = kwargs.get("query", "")
                layers_str = kwargs.get("layers", ["WORKING", "EPISODIC", "SEMANTIC"])
                top_k = kwargs.get("top_k", 5)

                if not query:
                    return ToolResult(
                        success=False,
                        tool_name=self.meta.name,
                        error="No query provided"
                    )

                # Convert string layer names to enum
                layers = []
                for layer_str in layers_str:
                    try:
                        layers.append(MemoryLayer[layer_str.upper()])
                    except KeyError:
                        continue

                if not layers:
                    return ToolResult(
                        success=False,
                        tool_name=self.meta.name,
                        error="No valid layers specified"
                    )

                results = await self.memory_core.recall(
                    query=query,
                    layers=layers,
                    top_k=top_k
                )

                return ToolResult(
                    success=True,
                    tool_name=self.meta.name,
                    data=[
                        {
                            "content": item.content,
                            "layer": item.layer.name,
                            "timestamp": item.timestamp.isoformat(),
                            "confidence": item.confidence_score
                        }
                        for item in results
                    ],
                    execution_time_ms=(time.time() - start_time) * 1000,
                    metadata={"query": query, "count": len(results)}
                )

            elif action == "write":
                content = kwargs.get("content", "")
                layer_str = kwargs.get("layer", "WORKING")

                if not content:
                    return ToolResult(
                        success=False,
                        tool_name=self.meta.name,
                        error="No content provided"
                    )

                try:
                    layer = MemoryLayer[layer_str.upper()]
                except KeyError:
                    return ToolResult(
                        success=False,
                        tool_name=self.meta.name,
                        error=f"Invalid layer: {layer_str}"
                    )

                memory_id = await self.memory_core.write(
                    content=content,
                    layer=layer,
                    metadata={"source": "tool"}
                )

                return ToolResult(
                    success=True,
                    tool_name=self.meta.name,
                    data=f"Memory written: {memory_id}",
                    execution_time_ms=(time.time() - start_time) * 1000,
                    metadata={"memory_id": memory_id, "layer": layer.name}
                )

            elif action == "consolidate":
                consolidated = await self.memory_core.consolidate()

                return ToolResult(
                    success=True,
                    tool_name=self.meta.name,
                    data=f"Consolidated {consolidated} memories",
                    execution_time_ms=(time.time() - start_time) * 1000,
                    metadata={"consolidated_count": consolidated}
                )

            elif action == "stats":
                stats = self.memory_core.get_stats()

                return ToolResult(
                    success=True,
                    tool_name=self.meta.name,
                    data=stats,
                    execution_time_ms=(time.time() - start_time) * 1000
                )

            else:
                return ToolResult(
                    success=False,
                    tool_name=self.meta.name,
                    error=f"Unknown action: {action}"
                )

        except Exception as e:
            logger.exception("memory.tool.error", action=action, error=str(e))
            return ToolResult(
                success=False,
                tool_name=self.meta.name,
                error=f"Memory operation failed: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )

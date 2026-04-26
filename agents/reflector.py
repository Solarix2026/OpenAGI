# agents/reflector.py
"""Post-execution reflection — The Meta-Cognition Layer (M).

Reflects on execution results and updates memory.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import structlog

from agents.planner import Planner, TaskNode, TaskStatus
from memory.memory_core import MemoryCore, MemoryLayer
from core.telos_core import TelosCore

logger = structlog.get_logger()


@dataclass
class ReflectionResult:
    """Result of reflecting on execution."""
    overall_success: bool
    lessons_learned: list[str] = field(default_factory=list)
    memory_updates: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class Reflector:
    """Post-execution reflection and learning."""

    def __init__(self,
        memory: MemoryCore,
        telos: Optional[TelosCore] = None
    ):
        self.memory = memory
        self.telos = telos
        logger.info("reflector.initialized")

    async def reflect(self, planner: Planner) -> ReflectionResult:
        """Reflect on completed plan execution."""
        import time
        start_time = time.time()

        lessons = []
        memory_updates = 0

        for task_id, node in planner.graph.nodes.items():
            if node.status == TaskStatus.COMPLETED:
                lesson = await self._extract_lesson(node)
                if lesson:
                    lessons.append(lesson)
                    await self._store_lesson(node, lesson)
                    memory_updates += 1

        logger.info("reflector.reflection_complete",
            lessons=len(lessons),
            memory_updates=memory_updates)

        return ReflectionResult(
            overall_success=planner.all_complete(),
            lessons_learned=lessons,
            memory_updates=memory_updates,
            metadata={
                "execution_time_ms": (time.time() - start_time) * 1000,
                "task_count": len(planner.graph.nodes)
            }
        )

    async def _extract_lesson(self, node: TaskNode) -> Optional[str]:
        """Extract a lesson from a successful task."""
        if not node.result:
            return None
        return f"Completed '{node.description}' using tool '{node.assigned_tool}'"

    async def _store_lesson(self, node: TaskNode, lesson: str) -> None:
        """Store successful lesson in procedural memory."""
        await self.memory.write(
            content=lesson,
            layer=MemoryLayer.PROCEDURAL,
            metadata={
                "task_id": node.task_id,
                "success": True,
                "tool_used": node.assigned_tool
            }
        )

    async def consolidate_memories(self) -> int:
        """Trigger memory consolidation."""
        return await self.memory.consolidate()

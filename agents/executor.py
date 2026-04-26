# agents/executor.py
"""Task executor — The Execution Engine (E).

Executes tasks from the planner using the tool registry.
Supports parallel execution of independent tasks.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator, Optional

import structlog

from agents.planner import Planner, TaskNode, TaskStatus
from tools.registry import ToolRegistry
from core.telos_core import TelosCore

logger = structlog.get_logger()


@dataclass
class ExecutionResult:
    """Result of executing a single task."""
    task_id: str
    success: bool
    output: Any = None
    error: str = ""
    tool_used: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class Executor:
    """Execute tasks from the planner graph."""

    def __init__(self,
        planner: Planner,
        registry: ToolRegistry,
        telos: Optional[TelosCore] = None
    ):
        self.planner = planner
        self.registry = registry
        self.telos = telos
        self.results: dict[str, ExecutionResult] = {}
        logger.info("executor.initialized")

    async def execute_task(self, task: TaskNode) -> ExecutionResult:
        """Execute a single task."""
        import time
        start_time = time.time()

        task.status = TaskStatus.IN_PROGRESS
        logger.info("executor.task_started", task_id=task.task_id)

        try:
            if task.assigned_tool:
                result = await self.registry.invoke(
                    task.assigned_tool,
                    task.parameters
                )

                exec_result = ExecutionResult(
                    task_id=task.task_id,
                    success=result.success,
                    output=result.data,
                    error=result.error,
                    tool_used=task.assigned_tool,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    metadata=result.metadata
                )
            else:
                relevant_tools = self.registry.discover(task.description, top_k=3)

                if not relevant_tools:
                    exec_result = ExecutionResult(
                        task_id=task.task_id,
                        success=False,
                        error=f"No suitable tool found for: {task.description}"
                    )
                else:
                    best_tool = relevant_tools[0]
                    result = await self.registry.invoke(best_tool.name, task.parameters)

                    exec_result = ExecutionResult(
                        task_id=task.task_id,
                        success=result.success,
                        output=result.data,
                        error=result.error,
                        tool_used=best_tool.name,
                        execution_time_ms=(time.time() - start_time) * 1000,
                        metadata=result.metadata
                    )

        except Exception as e:
            logger.exception("executor.task_error", task_id=task.task_id, error=str(e))
            exec_result = ExecutionResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )

        new_status = TaskStatus.COMPLETED if exec_result.success else TaskStatus.FAILED
        self.planner.update_task_status(task.task_id, new_status, exec_result.output)
        self.results[task.task_id] = exec_result

        logger.info("executor.task_completed",
            task_id=task.task_id,
            success=exec_result.success)

        return exec_result

    async def execute_plan(self) -> AsyncIterator[ExecutionResult]:
        """Execute the entire plan."""
        if self.planner.has_cycles():
            logger.error("executor.cycle_detected_in_plan")
            return

        levels = self.planner.get_parallel_branches()

        for level_idx, level in enumerate(levels):
            logger.info("executor.level_started", level=level_idx, tasks=len(level))

            tasks = [self.execute_task(task) for task in level]

            if len(tasks) == 1:
                result = await tasks[0]
                yield result
            else:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        logger.error("executor.parallel_error", error=str(result))
                    else:
                        yield result

            logger.info("executor.level_completed", level=level_idx)

    async def execute_sequential(self) -> list[ExecutionResult]:
        """Execute all ready tasks sequentially."""
        all_results = []

        while not self.planner.all_complete():
            ready = self.planner.get_ready_tasks()

            if not ready:
                pending = [n for n in self.planner.graph.nodes.values()
                          if n.status in (TaskStatus.PENDING, TaskStatus.READY)]
                if pending:
                    logger.warning("executor.blocked_tasks", count=len(pending))
                break

            for task in ready:
                result = await self.execute_task(task)
                all_results.append(result)

        return all_results

    def get_summary(self) -> dict[str, Any]:
        """Get execution summary."""
        results = list(self.results.values())
        total = len(results)
        successful = sum(1 for r in results if r.success)
        failed = total - successful
        total_time = sum(r.execution_time_ms for r in results)

        return {
            "total_tasks": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0,
            "total_time_ms": total_time,
            "tools_used": list(set(r.tool_used for r in results if r.tool_used))
        }

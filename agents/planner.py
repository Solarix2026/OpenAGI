# agents/planner.py
"""DAG-based task planner — The Policy Space (Π).

Plans are directed acyclic graphs, NOT linear lists.
Supports parallel branches where dependencies allow.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Optional

import structlog

from core.telos_core import TelosCore

logger = structlog.get_logger()


class TaskStatus(Enum):
    """Status of a task in the plan."""
    PENDING = auto()
    READY = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    SKIPPED = auto()


@dataclass
class TaskNode:
    """A single task in the DAG plan."""
    task_id: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    assigned_tool: Optional[str] = None
    parameters: dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskGraph:
    """A DAG of tasks."""
    nodes: dict[str, TaskNode] = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)


class Planner:
    """
    DAG-based task planner.

    Plans are directed acyclic graphs where:
    - Each node is a task
    - Edges represent dependencies
    - Parallel branches execute concurrently
    - Cycles are detected and rejected

    The planner coordinates with Telos to validate goals.
    """

    def __init__(self, telos: Optional[TelosCore] = None):
        self.graph = TaskGraph()
        self.telos = telos
        logger.info("planner.initialized")

    def create_plan(self, goals: list[str]) -> TaskGraph:
        """
        Create a DAG plan from goal descriptions.

        Each goal becomes a task node.
        Dependencies are inferred from goal ordering.
        """
        self.graph = TaskGraph()

        for i, goal in enumerate(goals):
            task_id = f"task_{i + 1}"

            # Validate goal against Telos
            if self.telos and self.telos.is_drift_critical(goal):
                logger.warning(
                    "planner.goal_drift_detected",
                    goal=goal,
                    drift=self.telos.drift_score(goal)
                )
                continue

            # Tasks depend on all previous tasks by default
            dependencies = [f"task_{j + 1}" for j in range(i)] if i > 0 else []

            self.add_task(task_id, goal, dependencies)

        logger.info("planner.plan_created", tasks=len(self.graph.nodes))
        return self.graph

    def add_task(
        self,
        task_id: str,
        description: str,
        dependencies: list[str] = None,
        assigned_tool: Optional[str] = None,
        parameters: dict[str, Any] = None
    ) -> TaskNode:
        """Add a task to the graph."""
        if dependencies is None:
            dependencies = []

        node = TaskNode(
            task_id=task_id,
            description=description,
            dependencies=dependencies,
            assigned_tool=assigned_tool,
            parameters=parameters or {}
        )

        self.graph.nodes[task_id] = node

        # Add edges for dependencies
        for dep_id in dependencies:
            self.graph.edges.append((dep_id, task_id))

        logger.debug("planner.task_added", task_id=task_id, dependencies=dependencies)
        return node

    def has_cycles(self) -> bool:
        """Detect cycles in the DAG using DFS."""
        visited = set()
        rec_stack = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            # Check all outgoing edges
            for src, dst in self.graph.edges:
                if src == node_id:
                    if dst not in visited:
                        if dfs(dst):
                            return True
                    elif dst in rec_stack:
                        return True

            rec_stack.discard(node_id)
            return False

        for node_id in self.graph.nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True

        return False

    def get_ready_tasks(self) -> list[TaskNode]:
        """Get tasks whose dependencies are all satisfied."""
        ready = []

        for node_id, node in self.graph.nodes.items():
            if node.status not in (TaskStatus.PENDING, TaskStatus.READY):
                continue

            # Check all dependencies are completed
            all_deps_met = True
            for dep_id in node.dependencies:
                dep_node = self.graph.nodes.get(dep_id)
                if dep_node is None or dep_node.status != TaskStatus.COMPLETED:
                    all_deps_met = False
                    break

            if all_deps_met:
                node.status = TaskStatus.READY
                ready.append(node)

        return ready

    def update_task_status(self, task_id: str, status: TaskStatus, result: Any = None) -> None:
        """Update task status."""
        if task_id not in self.graph.nodes:
            logger.warning("planner.task_not_found", task_id=task_id)
            return

        node = self.graph.nodes[task_id]
        node.status = status

        if status == TaskStatus.COMPLETED:
            node.completed_at = datetime.utcnow()

        if result is not None:
            node.result = result

        logger.debug("planner.task_updated", task_id=task_id, status=status.name)

    def get_execution_order(self) -> list[TaskNode]:
        """Return tasks in topological order (dependency-respecting)."""
        if self.has_cycles():
            logger.error("planner.cycle_detected")
            return []

        visited = set()
        order = []

        def visit(node_id: str) -> None:
            if node_id in visited:
                return
            visited.add(node_id)

            # Visit all dependencies first
            for dep_id in self.graph.nodes[node_id].dependencies:
                visit(dep_id)

            order.append(self.graph.nodes[node_id])

        for node_id in self.graph.nodes:
            visit(node_id)

        return order

    def get_parallel_branches(self) -> list[list[TaskNode]]:
        """Group tasks into parallel execution levels."""
        if self.has_cycles():
            return []

        levels = []
        remaining = set(self.graph.nodes.keys())

        while remaining:
            # Find tasks with no unprocessed dependencies
            current_level = []
            for node_id in list(remaining):
                node = self.graph.nodes[node_id]
                if all(dep not in remaining for dep in node.dependencies):
                    current_level.append(node)

            if not current_level:
                break

            levels.append(current_level)
            remaining -= {n.task_id for n in current_level}

        return levels

    def all_complete(self) -> bool:
        """Check if all tasks are complete."""
        return all(
            node.status == TaskStatus.COMPLETED
            for node in self.graph.nodes.values()
        )

    def get_summary(self) -> dict[str, Any]:
        """Get plan execution summary."""
        total = len(self.graph.nodes)
        completed = sum(1 for n in self.graph.nodes.values() if n.status == TaskStatus.COMPLETED)
        failed = sum(1 for n in self.graph.nodes.values() if n.status == TaskStatus.FAILED)
        in_progress = sum(1 for n in self.graph.nodes.values() if n.status == TaskStatus.IN_PROGRESS)

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": total - completed - failed - in_progress,
            "progress_pct": (completed / total * 100) if total > 0 else 0
        }
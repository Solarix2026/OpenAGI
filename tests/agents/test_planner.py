# tests/agents/test_planner.py
import pytest
from agents.planner import Planner, TaskNode, TaskGraph, TaskStatus


def test_planner_creates_empty_graph():
    """Planner initializes with empty task graph."""
    planner = Planner()

    assert planner.graph is not None
    assert len(planner.graph.nodes) == 0


def test_task_node_creation():
    """TaskNode captures task information."""
    node = TaskNode(
        task_id="task1",
        description="Test task",
        dependencies=[],
        status=TaskStatus.PENDING
    )

    assert node.task_id == "task1"
    assert node.description == "Test task"
    assert node.status == TaskStatus.PENDING


def test_planner_adds_task():
    """Planner can add tasks to graph."""
    planner = Planner()

    planner.add_task("task1", "First task")

    assert len(planner.graph.nodes) == 1
    assert "task1" in planner.graph.nodes


def test_planner_adds_dependencies():
    """Planner can add task dependencies."""
    planner = Planner()

    planner.add_task("task1", "First task")
    planner.add_task("task2", "Second task", dependencies=["task1"])

    assert len(planner.graph.nodes) == 2
    assert len(planner.graph.edges) == 1


def test_planner_detects_cycles():
    """Planner detects circular dependencies."""
    planner = Planner()

    planner.add_task("task1", "First task", dependencies=["task2"])
    planner.add_task("task2", "Second task", dependencies=["task1"])

    has_cycles = planner.has_cycles()
    assert has_cycles is True


def test_planner_gets_ready_tasks():
    """Planner identifies tasks ready to execute."""
    planner = Planner()

    planner.add_task("task1", "First task")
    planner.add_task("task2", "Second task", dependencies=["task1"])

    ready = planner.get_ready_tasks()
    assert len(ready) == 1
    assert ready[0].task_id == "task1"


def test_planner_updates_task_status():
    """Planner can update task status."""
    planner = Planner()

    planner.add_task("task1", "First task")
    planner.update_task_status("task1", TaskStatus.COMPLETED)

    node = planner.graph.nodes["task1"]
    assert node.status == TaskStatus.COMPLETED


def test_planner_topological_sort():
    """Planner returns tasks in dependency order."""
    planner = Planner()

    planner.add_task("task1", "First task")
    planner.add_task("task2", "Second task", dependencies=["task1"])
    planner.add_task("task3", "Third task", dependencies=["task2"])

    ordered = planner.get_execution_order()
    assert len(ordered) == 3
    assert ordered[0].task_id == "task1"
    assert ordered[1].task_id == "task2"
    assert ordered[2].task_id == "task3"

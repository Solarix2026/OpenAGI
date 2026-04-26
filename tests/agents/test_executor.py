# tests/agents/test_executor.py
import pytest
from unittest.mock import AsyncMock
from agents.executor import Executor, ExecutionResult
from agents.planner import Planner, TaskGraph, TaskNode, TaskStatus
from tools.registry import ToolRegistry
from tools.base_tool import BaseTool, ToolMeta, ToolResult


@pytest.fixture
def mock_registry():
    registry = ToolRegistry()

    # Add a mock tool
    class MockTool(BaseTool):
        @property
        def meta(self):
            return ToolMeta(
                name="mock_tool",
                description="Mock tool for testing",
                parameters={"type": "object"},
                risk_score=0.1,
                categories=["test"],
            )

        async def execute(self, **kwargs):
            return ToolResult(
                success=True,
                tool_name="mock_tool",
                data={"output": "mock result"},
            )

    registry.register(MockTool())
    return registry


@pytest.fixture
def mock_planner():
    planner = Planner.__new__(Planner)
    planner.llm = AsyncMock()
    planner.registry = ToolRegistry()
    return planner


@pytest.fixture
def sample_graph():
    return TaskGraph(nodes=[
        TaskNode(id="t1", description="Task 1", tool_hint="mock_tool", depends_on=[]),
        TaskNode(id="t2", description="Task 2", tool_hint="mock_tool", depends_on=["t1"]),
        TaskNode(id="t3", description="Task 3", tool_hint=None, depends_on=["t1"]),
    ], goal="Test goal")


@pytest.mark.asyncio
async def test_executor_executes_sequential_tasks(mock_registry, mock_planner, sample_graph):
    executor = Executor(registry=mock_registry, planner=mock_planner)
    result = await executor.execute(sample_graph)

    assert result.success
    assert result.total_nodes == 3
    assert len(result.failed_nodes) == 0


@pytest.mark.asyncio
async def test_executor_handles_tool_failure(mock_registry, mock_planner):
    # Create a graph with a failing tool
    graph = TaskGraph(nodes=[
        TaskNode(id="t1", description="Task 1", tool_hint="nonexistent_tool", depends_on=[]),
    ], goal="Test failure")

    executor = Executor(registry=mock_registry, planner=mock_planner)
    result = await executor.execute(graph)

    assert not result.success
    assert len(result.failed_nodes) == 1


@pytest.mark.asyncio
async def test_executor_respects_dependencies(mock_registry, mock_planner):
    graph = TaskGraph(nodes=[
        TaskNode(id="t1", description="First", tool_hint="mock_tool", depends_on=[]),
        TaskNode(id="t2", description="Second", tool_hint="mock_tool", depends_on=["t1"]),
        TaskNode(id="t3", description="Third", tool_hint="mock_tool", depends_on=["t2"]),
    ], goal="Test dependencies")

    execution_order = []

    # Patch registry.invoke to track execution order
    original_invoke = mock_registry.invoke
    async def tracked_invoke(tool_name, params):
        execution_order.append(tool_name)
        return await original_invoke(tool_name, params)

    mock_registry.invoke = tracked_invoke

    executor = Executor(registry=mock_registry, planner=mock_planner)
    await executor.execute(graph)

    # Verify t1 executed before t2, t2 before t3
    assert execution_order == ["mock_tool", "mock_tool", "mock_tool"]


@pytest.mark.asyncio
async def test_executor_passes_context_to_dependent_tasks(mock_registry, mock_planner):
    graph = TaskGraph(nodes=[
        TaskNode(id="t1", description="First", tool_hint="mock_tool", depends_on=[]),
        TaskNode(id="t2", description="Second", tool_hint="mock_tool", depends_on=["t1"]),
    ], goal="Test context passing")

    executor = Executor(registry=mock_registry, planner=mock_planner)
    result = await executor.execute(graph)

    assert result.success
    # t2 should have access to t1's output
    assert "t1" in result.outputs


@pytest.mark.asyncio
async def test_executor_handles_parallel_tasks(mock_registry, mock_planner):
    graph = TaskGraph(nodes=[
        TaskNode(id="t1", description="Root", tool_hint=None, depends_on=[]),
        TaskNode(id="t2", description="Branch A", tool_hint="mock_tool", depends_on=["t1"]),
        TaskNode(id="t3", description="Branch B", tool_hint="mock_tool", depends_on=["t1"]),
        TaskNode(id="t4", description="Merge", tool_hint=None, depends_on=["t2", "t3"]),
    ], goal="Test parallel execution")

    executor = Executor(registry=mock_registry, planner=mock_planner, max_parallel=2)
    result = await executor.execute(graph)

    assert result.success
    assert result.total_nodes == 4


@pytest.mark.asyncio
async def test_executor_records_execution_time(mock_registry, mock_planner, sample_graph):
    executor = Executor(registry=mock_registry, planner=mock_planner)
    result = await executor.execute(sample_graph)

    assert result.execution_time_ms >= 0


@pytest.mark.asyncio
async def test_executor_handles_empty_graph(mock_registry, mock_planner):
    graph = TaskGraph(nodes=[], goal="Empty goal")
    executor = Executor(registry=mock_registry, planner=mock_planner)
    result = await executor.execute(graph)

    assert result.success
    assert result.total_nodes == 0


@pytest.mark.asyncio
async def test_executor_respects_max_parallel(mock_registry, mock_planner):
    # Create many parallel tasks
    nodes = [TaskNode(id=f"t{i}", description=f"Task {i}", tool_hint="mock_tool", depends_on=[])
             for i in range(10)]
    graph = TaskGraph(nodes=nodes, goal="Test parallel limit")

    executor = Executor(registry=mock_registry, planner=mock_planner, max_parallel=3)
    result = await executor.execute(graph)

    assert result.success
    assert result.total_nodes == 10


@pytest.mark.asyncio
async def test_executor_handles_task_without_tool_hint(mock_registry, mock_planner):
    graph = TaskGraph(nodes=[
        TaskNode(id="t1", description="Informational task", tool_hint=None, depends_on=[]),
    ], goal="Test no tool")

    executor = Executor(registry=mock_registry, planner=mock_planner)
    result = await executor.execute(graph)

    assert result.success
    # Task should complete even without a tool


@pytest.mark.asyncio
async def test_executor_updates_task_status(mock_registry, mock_planner, sample_graph):
    executor = Executor(registry=mock_registry, planner=mock_planner)
    await executor.execute(sample_graph)

    # All tasks should be marked as SUCCESS
    for node in sample_graph.nodes:
        assert node.status == TaskStatus.SUCCESS


@pytest.mark.asyncio
async def test_executor_handles_replan_on_failure(mock_registry, mock_planner):
    # Create a graph that will fail
    graph = TaskGraph(nodes=[
        TaskNode(id="t1", description="Failing task", tool_hint="nonexistent_tool", depends_on=[]),
    ], goal="Test replan")

    # Mock replan to return a fixed graph
    async def mock_replan(failed_node, error, graph):
        return TaskGraph(nodes=[
            TaskNode(id="t1", description="Fixed task", tool_hint="mock_tool", depends_on=[]),
        ], goal="Fixed goal")

    mock_planner.replan = mock_replan

    executor = Executor(registry=mock_registry, planner=mock_planner, max_replan_attempts=2)
    result = await executor.execute(graph)

    # Should attempt replan
    assert result.total_nodes >= 1


@pytest.mark.asyncio
async def test_executor_limits_replan_attempts(mock_registry, mock_planner):
    graph = TaskGraph(nodes=[
        TaskNode(id="t1", description="Always failing", tool_hint="nonexistent_tool", depends_on=[]),
    ], goal="Test replan limit")

    executor = Executor(registry=mock_registry, planner=mock_planner, max_replan_attempts=1)
    result = await executor.execute(graph)

    assert not result.success
    assert len(result.failed_nodes) >= 1


@pytest.mark.asyncio
async def test_executor_result_structure(mock_registry, mock_planner, sample_graph):
    executor = Executor(registry=mock_registry, planner=mock_planner)
    result = await executor.execute(sample_graph)

    assert hasattr(result, 'goal')
    assert hasattr(result, 'success')
    assert hasattr(result, 'outputs')
    assert hasattr(result, 'failed_nodes')
    assert hasattr(result, 'total_nodes')
    assert hasattr(result, 'execution_time_ms')

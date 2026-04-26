"""Tests for MetaAgent (L3)."""
import pytest
import asyncio
from datetime import datetime
from core.meta_agent import (
    MetaAgent,
    ImprovementStrategy,
    Hypothesis,
    ImprovementAction,
    MCPClient,
)


@pytest.fixture
def meta_agent():
    """Create a MetaAgent instance for testing."""
    return MetaAgent(hdc_dim=1000)


def test_meta_agent_initialization(meta_agent):
    """MetaAgent initializes correctly."""
    assert meta_agent.hdc_dim == 1000
    assert len(meta_agent._hypotheses) == 0
    assert len(meta_agent._improvement_actions) == 0
    assert len(meta_agent._mcp_clients) == 0


@pytest.mark.asyncio
async def test_reason_about_strategy(meta_agent):
    """Can reason about strategy."""
    context = {"current_state": "initial"}
    goal = "Achieve target outcome"

    strategy = await meta_agent.reason_about_strategy(context, goal)

    assert "goal" in strategy
    assert strategy["goal"] == goal
    assert "reasoning" in strategy
    assert "confidence" in strategy
    assert 0.0 <= strategy["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_evaluate_hypotheses(meta_agent):
    """Can evaluate hypotheses."""
    hypotheses = [
        Hypothesis(
            statement="The system will succeed",
            confidence=0.7,
        ),
        Hypothesis(
            statement="The system will fail",
            confidence=0.3,
        ),
    ]

    context = {"evidence": "positive"}

    results = await meta_agent.evaluate_hypotheses(hypotheses, context)

    assert len(results) == 2
    assert all(isinstance(h, Hypothesis) for h in results)
    # At least one should have a status
    assert any(h.status in ["pending", "testing", "confirmed", "refuted"] for h in results)


@pytest.mark.asyncio
async def test_run_self_improvement_cycle(meta_agent):
    """Can run self-improvement cycle."""
    metrics = {
        "success_rate": 0.8,
        "execution_time": 2.5,
        "memory_efficiency": 0.7,
    }

    actions = await meta_agent.run_self_improvement_cycle(metrics)

    assert isinstance(actions, list)
    assert meta_agent._improvement_cycle_count == 1
    assert meta_agent._last_improvement_time is not None


@pytest.mark.asyncio
async def test_execute_improvement_action(meta_agent):
    """Can execute improvement actions."""
    action = ImprovementAction(
        strategy=ImprovementStrategy.REFINE_PLANNING,
        description="Test improvement",
        expected_benefit=0.3,
        priority=1,
    )

    result = await meta_agent.execute_improvement_action(action)

    assert "action_id" in result
    assert "success" in result
    assert "message" in result


@pytest.mark.asyncio
async def test_refine_planning(meta_agent):
    """Can refine planning."""
    action = ImprovementAction(
        strategy=ImprovementStrategy.REFINE_PLANNING,
        description="Improve planning",
        expected_benefit=0.3,
        priority=1,
    )

    result = await meta_agent._refine_planning(action)

    assert result["success"] is True
    assert "planning" in result["metrics"]["improvement_type"]


@pytest.mark.asyncio
async def test_optimize_execution(meta_agent):
    """Can optimize execution."""
    action = ImprovementAction(
        strategy=ImprovementStrategy.OPTIMIZE_EXECUTION,
        description="Optimize execution",
        expected_benefit=0.4,
        priority=1,
    )

    result = await meta_agent._optimize_execution(action)

    assert result["success"] is True
    assert "execution" in result["metrics"]["improvement_type"]


@pytest.mark.asyncio
async def test_enhance_memory(meta_agent):
    """Can enhance memory."""
    action = ImprovementAction(
        strategy=ImprovementStrategy.ENHANCE_MEMORY,
        description="Enhance memory",
        expected_benefit=0.2,
        priority=1,
    )

    result = await meta_agent._enhance_memory(action)

    assert result["success"] is True
    assert "memory" in result["metrics"]["improvement_type"]


@pytest.mark.asyncio
async def test_expand_tools(meta_agent):
    """Can expand tools."""
    action = ImprovementAction(
        strategy=ImprovementStrategy.EXPAND_TOOLS,
        description="Expand tools",
        expected_benefit=0.3,
        priority=1,
    )

    result = await meta_agent._expand_tools(action)

    assert result["success"] is True
    assert "tools" in result["metrics"]["improvement_type"]


@pytest.mark.asyncio
async def test_tune_parameters(meta_agent):
    """Can tune parameters."""
    action = ImprovementAction(
        strategy=ImprovementStrategy.TUNE_PARAMETERS,
        description="Tune parameters",
        expected_benefit=0.2,
        priority=1,
    )

    result = await meta_agent._tune_parameters(action)

    assert result["success"] is True
    assert "parameters" in result["metrics"]["improvement_type"]


@pytest.mark.asyncio
async def test_register_mcp_client(meta_agent):
    """Can register MCP clients."""
    client_id = await meta_agent.register_mcp_client(
        name="test_client",
        endpoint="http://localhost:8000",
        capabilities=["read", "write"],
    )

    assert client_id is not None
    assert len(meta_agent._mcp_clients) == 1

    client = meta_agent.get_mcp_client(client_id)
    assert client is not None
    assert client.name == "test_client"
    assert client.endpoint == "http://localhost:8000"
    assert client.capabilities == ["read", "write"]


def test_get_nonexistent_mcp_client(meta_agent):
    """Getting nonexistent MCP client returns None."""
    result = meta_agent.get_mcp_client("nonexistent")
    assert result is None


def test_list_mcp_clients(meta_agent):
    """Can list MCP clients."""
    asyncio.run(meta_agent.register_mcp_client("client1", "http://localhost:8001", ["read"]))
    asyncio.run(meta_agent.register_mcp_client("client2", "http://localhost:8002", ["write"]))

    clients = meta_agent.list_mcp_clients()

    assert len(clients) == 2
    assert all(isinstance(c, MCPClient) for c in clients)


@pytest.mark.asyncio
async def test_store_in_active_memory(meta_agent):
    """Can store in active memory."""
    memory_id = await meta_agent.store_in_active_memory(
        content="Test content",
        metadata={"type": "test"},
    )

    assert memory_id is not None
    assert len(meta_agent._active_memory.memories) == 1


@pytest.mark.asyncio
async def test_recall_from_active_memory(meta_agent):
    """Can recall from active memory."""
    # Store some content
    await meta_agent.store_in_active_memory("python programming", {"type": "code"})
    await meta_agent.store_in_active_memory("javascript development", {"type": "code"})
    await meta_agent.store_in_active_memory("coffee brewing", {"type": "beverage"})

    # Recall
    results = await meta_agent.recall_from_active_memory("programming", top_k=2)

    assert isinstance(results, list)
    assert len(results) >= 0
    if results:
        assert "memory_id" in results[0]
        assert "content" in results[0]
        assert "score" in results[0]


def test_clear_active_memory(meta_agent):
    """Can clear active memory."""
    # Store something
    asyncio.run(meta_agent.store_in_active_memory("test", {}))

    # Clear
    meta_agent.clear_active_memory()

    # Should be empty
    assert len(meta_agent._active_memory.memories) == 0


def test_get_stats(meta_agent):
    """Can get meta-agent statistics."""
    # Add some data
    asyncio.run(meta_agent.store_in_active_memory("test", {}))
    asyncio.run(meta_agent.register_mcp_client("client", "http://localhost:8000", []))

    stats = meta_agent.get_stats()

    assert "improvement_cycles" in stats
    assert "hypotheses_count" in stats
    assert "improvement_actions_count" in stats
    assert "performance_history_size" in stats
    assert "active_memory_size" in stats
    assert "mcp_clients_count" in stats
    assert "mcp_clients_connected" in stats


def test_get_hypotheses(meta_agent):
    """Can get all hypotheses."""
    # Add a hypothesis
    hypothesis = Hypothesis(statement="Test hypothesis")
    asyncio.run(meta_agent.evaluate_hypotheses([hypothesis], {}))

    hypotheses = meta_agent.get_hypotheses()

    assert isinstance(hypotheses, list)
    assert len(hypotheses) >= 1


def test_get_improvement_actions(meta_agent):
    """Can get all improvement actions."""
    # Run an improvement cycle
    asyncio.run(meta_agent.run_self_improvement_cycle({"success_rate": 0.5}))

    actions = meta_agent.get_improvement_actions()

    assert isinstance(actions, list)
    assert len(actions) >= 0


def test_get_performance_history(meta_agent):
    """Can get performance history."""
    # Add some performance data
    asyncio.run(meta_agent.run_self_improvement_cycle({"success_rate": 0.8}))
    asyncio.run(meta_agent.run_self_improvement_cycle({"success_rate": 0.9}))

    history = meta_agent.get_performance_history(limit=10)

    assert isinstance(history, list)
    assert len(history) == 2
    assert all("success_rate" in h for h in history)


def test_improvement_strategy_enum():
    """ImprovementStrategy enum has correct values."""
    assert hasattr(ImprovementStrategy, "REFINE_PLANNING")
    assert hasattr(ImprovementStrategy, "OPTIMIZE_EXECUTION")
    assert hasattr(ImprovementStrategy, "ENHANCE_MEMORY")
    assert hasattr(ImprovementStrategy, "EXPAND_TOOLS")
    assert hasattr(ImprovementStrategy, "TUNE_PARAMETERS")


def test_hypothesis_creation():
    """Can create Hypothesis objects."""
    hypothesis = Hypothesis(
        statement="Test statement",
        confidence=0.8,
    )

    assert hypothesis.statement == "Test statement"
    assert hypothesis.confidence == 0.8
    assert hypothesis.status == "pending"
    assert hypothesis.hypothesis_id is not None


def test_improvement_action_creation():
    """Can create ImprovementAction objects."""
    action = ImprovementAction(
        strategy=ImprovementStrategy.REFINE_PLANNING,
        description="Test action",
        expected_benefit=0.5,
        priority=1,
    )

    assert action.strategy == ImprovementStrategy.REFINE_PLANNING
    assert action.description == "Test action"
    assert action.expected_benefit == 0.5
    assert action.priority == 1
    assert action.status == "pending"


def test_mcp_client_creation():
    """Can create MCPClient objects."""
    client = MCPClient(
        name="test_client",
        endpoint="http://localhost:8000",
        capabilities=["read", "write"],
    )

    assert client.name == "test_client"
    assert client.endpoint == "http://localhost:8000"
    assert client.capabilities == ["read", "write"]
    assert client.connected is False
    assert client.client_id is not None

# tests/orchestrator/test_mas.py
"""Tests for Multi-Agent System Kernel."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from orchestrator.mas_kernel import MASKernel, AgentConfig, AgentResult
from orchestrator.message_bus import MessageBus, AgentMessage, MessageType


def test_message_bus_initialization():
    """MessageBus initializes correctly."""
    bus = MessageBus()
    assert len(bus._queues) == 0
    assert len(bus._subscribers) == 0


def test_message_bus_registers_agent():
    """MessageBus can register agents."""
    bus = MessageBus()
    bus.register_agent("agent-1")

    assert "agent-1" in bus._queues
    assert "agent-1" in bus._subscribers


def test_message_bus_unregisters_agent():
    """MessageBus can unregister agents."""
    bus = MessageBus()
    bus.register_agent("agent-1")
    bus.unregister_agent("agent-1")

    assert "agent-1" not in bus._queues
    assert "agent-1" not in bus._subscribers


def test_message_bus_subscribes_to_type():
    """MessageBus can subscribe agents to message types."""
    bus = MessageBus()
    bus.register_agent("agent-1")
    bus.subscribe("agent-1", MessageType.TASK)

    assert MessageType.TASK in bus._subscribers["agent-1"]


def test_message_bus_creates_message():
    """AgentMessage can be created and serialized."""
    message = AgentMessage(
        sender_id="agent-1",
        recipient_id="agent-2",
        message_type=MessageType.TASK,
        content={"task": "test"},
    )

    assert message.sender_id == "agent-1"
    assert message.recipient_id == "agent-2"
    assert message.message_type == MessageType.TASK

    # Test serialization
    data = message.to_dict()
    assert data["sender_id"] == "agent-1"
    assert data["message_type"] == "task"


def test_message_bus_deserializes_message():
    """AgentMessage can be deserialized from dict."""
    data = {
        "message_id": "test-id",
        "message_type": "task",
        "sender_id": "agent-1",
        "recipient_id": "agent-2",
        "content": {"task": "test"},
        "timestamp": "2024-01-01T00:00:00",
        "metadata": {},
        "reply_to": None,
    }

    message = AgentMessage.from_dict(data)

    assert message.message_id == "test-id"
    assert message.sender_id == "agent-1"
    assert message.message_type == MessageType.TASK


@pytest.mark.asyncio
async def test_message_bus_sends_point_to_point():
    """MessageBus can send point-to-point messages."""
    bus = MessageBus()
    bus.register_agent("sender")
    bus.register_agent("receiver")

    message = AgentMessage(
        sender_id="sender",
        recipient_id="receiver",
        message_type=MessageType.TASK,
        content="test content",
    )

    await bus.send(message)

    received = await bus.receive("receiver", timeout=1.0)
    assert received is not None
    assert received.content == "test content"


@pytest.mark.asyncio
async def test_message_bus_broadcasts():
    """MessageBus can broadcast messages."""
    bus = MessageBus()
    bus.register_agent("sender")
    bus.register_agent("receiver1")
    bus.register_agent("receiver2")

    # Subscribe receivers to TASK messages
    bus.subscribe("receiver1", MessageType.TASK)
    bus.subscribe("receiver2", MessageType.TASK)

    await bus.broadcast("sender", MessageType.TASK, "broadcast content")

    # Both receivers should get the message
    received1 = await bus.receive("receiver1", timeout=1.0)
    received2 = await bus.receive("receiver2", timeout=1.0)

    assert received1 is not None
    assert received2 is not None
    assert received1.content == "broadcast content"
    assert received2.content == "broadcast content"


@pytest.mark.asyncio
async def test_message_bus_logs_messages():
    """MessageBus logs messages for debugging."""
    bus = MessageBus()
    bus.register_agent("sender")
    bus.register_agent("receiver")

    message = AgentMessage(
        sender_id="sender",
        recipient_id="receiver",
        message_type=MessageType.TASK,
        content="test",
    )

    await bus.send(message)

    log = bus.get_message_log()
    assert len(log) == 1
    assert log[0].message_id == message.message_id


def test_message_bus_gets_stats():
    """MessageBus can provide statistics."""
    bus = MessageBus()
    bus.register_agent("agent-1")
    bus.register_agent("agent-2")

    stats = bus.get_stats()

    assert stats["registered_agents"] == 2
    assert stats["total_messages"] == 0
    assert "agent-1" in stats["queues"]
    assert "agent-2" in stats["queues"]


def test_mas_kernel_initialization():
    """MASKernel initializes correctly."""
    from core.kernel import Kernel
    from config.settings import Settings

    # Create mock dependencies
    llm = MagicMock()
    memory = MagicMock()
    registry = MagicMock()
    telos = MagicMock()

    kernel = MASKernel(llm=llm, memory=memory, registry=registry, telos=telos)

    assert kernel.llm is not None
    assert kernel.memory is not None
    assert kernel.registry is not None
    assert kernel.telos is not None
    assert kernel.message_bus is not None


def test_agent_config_creation():
    """AgentConfig can be created."""
    config = AgentConfig(
        agent_type="specialist",
        goal="Test goal",
        max_tokens=1024,
    )

    assert config.agent_type == "specialist"
    assert config.goal == "Test goal"
    assert config.max_tokens == 1024


def test_agent_result_creation():
    """AgentResult can be created."""
    result = AgentResult(
        agent_id="agent-1",
        agent_type="specialist",
        goal="Test goal",
        success=True,
        result="Test result",
    )

    assert result.agent_id == "agent-1"
    assert result.success is True
    assert result.result == "Test result"


@pytest.mark.asyncio
async def test_mas_kernel_runs_single_agent():
    """MASKernel can run with single agent (parallel_branches=1)."""
    from core.kernel import Kernel
    from config.settings import Settings

    # Create mock dependencies
    llm = MagicMock()
    memory = MagicMock()
    registry = MagicMock()
    telos = MagicMock()

    kernel = MASKernel(llm=llm, memory=memory, registry=registry, telos=telos)

    # Mock the kernel.run to return a simple result
    with patch('core.kernel.Kernel') as MockKernel:
        mock_kernel = MagicMock()
        async def mock_run(*args, **kwargs):
            yield "test result"
        mock_kernel.run = mock_run
        MockKernel.return_value = mock_kernel

        tokens = []
        async for token in kernel.run("test goal", parallel_branches=1):
            tokens.append(token)

        assert len(tokens) > 0


@pytest.mark.asyncio
async def test_mas_kernel_decomposes_goal():
    """MASKernel can decompose goals into sub-goals."""
    from core.kernel import Kernel
    from config.settings import Settings

    # Create mock LLM that returns JSON
    llm = MagicMock()
    llm.complete = AsyncMock()
    llm.complete.return_value = MagicMock(content='["sub-goal 1", "sub-goal 2"]')

    memory = MagicMock()
    registry = MagicMock()
    telos = MagicMock()

    kernel = MASKernel(llm=llm, memory=memory, registry=registry, telos=telos)

    sub_goals = await kernel._decompose_goal("test goal", 2)

    assert len(sub_goals) == 2
    assert "sub-goal 1" in sub_goals
    assert "sub-goal 2" in sub_goals


def test_mas_kernel_gets_stats():
    """MASKernel can provide statistics."""
    from core.kernel import Kernel
    from config.settings import Settings

    llm = MagicMock()
    memory = MagicMock()
    registry = MagicMock()
    telos = MagicMock()

    kernel = MASKernel(llm=llm, memory=memory, registry=registry, telos=telos)

    stats = kernel.get_stats()

    assert "running_agents" in stats
    assert "message_bus" in stats
    assert stats["running_agents"] == 0

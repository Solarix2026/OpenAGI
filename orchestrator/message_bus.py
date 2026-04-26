# orchestrator/message_bus.py
"""Message Bus — Inter-agent communication system.

Provides asynchronous communication between agents in the multi-agent system.
Supports:
- Point-to-point messaging
- Broadcast messaging
- Message queuing
- Message filtering
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

import structlog

logger = structlog.get_logger()


class MessageType(Enum):
    """Types of messages between agents."""
    TASK = "task"
    RESULT = "result"
    ERROR = "error"
    STATUS = "status"
    CONTROL = "control"
    QUERY = "query"
    RESPONSE = "response"


@dataclass
class AgentMessage:
    """A message between agents."""
    message_id: str = field(default_factory=lambda: str(uuid4()))
    message_type: MessageType = MessageType.TASK
    sender_id: str = ""
    recipient_id: str = ""  # Empty for broadcast
    content: Any = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    reply_to: Optional[str] = None  # Message ID this is replying to

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "reply_to": self.reply_to,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentMessage":
        """Create from dictionary."""
        return cls(
            message_id=data.get("message_id", ""),
            message_type=MessageType(data.get("message_type", "task")),
            sender_id=data.get("sender_id", ""),
            recipient_id=data.get("recipient_id", ""),
            content=data.get("content"),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat())),
            metadata=data.get("metadata", {}),
            reply_to=data.get("reply_to"),
        )


class MessageBus:
    """
    Asynchronous message bus for inter-agent communication.

    Supports:
    - Point-to-point messaging (sender → recipient)
    - Broadcast messaging (sender → all)
    - Message filtering by type
    - Message queuing per agent
    """

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}
        self._subscribers: dict[str, set[str]] = {}  # agent_id → set of message_types
        self._message_log: list[AgentMessage] = []
        self._max_log_size = 1000

    def register_agent(self, agent_id: str) -> None:
        """Register an agent with the message bus."""
        if agent_id not in self._queues:
            self._queues[agent_id] = asyncio.Queue()
            self._subscribers[agent_id] = set()
            logger.info("message_bus.agent_registered", agent_id=agent_id)

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from the message bus."""
        if agent_id in self._queues:
            del self._queues[agent_id]
        if agent_id in self._subscribers:
            del self._subscribers[agent_id]
        logger.info("message_bus.agent_unregistered", agent_id=agent_id)

    def subscribe(self, agent_id: str, message_type: MessageType) -> None:
        """Subscribe an agent to a specific message type."""
        if agent_id not in self._subscribers:
            self._subscribers[agent_id] = set()
        self._subscribers[agent_id].add(message_type)
        logger.debug("message_bus.subscribed", agent_id=agent_id, message_type=message_type.value)

    async def send(self, message: AgentMessage) -> None:
        """Send a message to its recipient(s)."""
        self._log_message(message)

        if message.recipient_id:
            # Point-to-point
            if message.recipient_id in self._queues:
                await self._queues[message.recipient_id].put(message)
                logger.debug("message_bus.sent_point_to_point", sender=message.sender_id, recipient=message.recipient_id)
            else:
                logger.warning("message_bus.recipient_not_found", recipient=message.recipient_id)
        else:
            # Broadcast to all subscribers of this message type
            for agent_id, subscribed_types in self._subscribers.items():
                if message.message_type in subscribed_types:
                    if agent_id in self._queues:
                        await self._queues[agent_id].put(message)
            logger.debug("message_bus.broadcast", sender=message.sender_id, message_type=message.message_type.value)

    async def receive(self, agent_id: str, timeout: Optional[float] = None) -> Optional[AgentMessage]:
        """Receive a message for an agent."""
        if agent_id not in self._queues:
            return None

        try:
            if timeout:
                return await asyncio.wait_for(self._queues[agent_id].get(), timeout=timeout)
            else:
                return await self._queues[agent_id].get()
        except asyncio.TimeoutError:
            return None

    async def broadcast(self, sender_id: str, message_type: MessageType, content: Any) -> None:
        """Broadcast a message to all agents."""
        message = AgentMessage(
            sender_id=sender_id,
            message_type=message_type,
            content=content,
        )
        await self.send(message)

    def _log_message(self, message: AgentMessage) -> None:
        """Log a message for debugging."""
        self._message_log.append(message)
        if len(self._message_log) > self._max_log_size:
            self._message_log.pop(0)

    def get_message_log(self, limit: int = 100) -> list[AgentMessage]:
        """Get recent message log."""
        return self._message_log[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Get message bus statistics."""
        return {
            "registered_agents": len(self._queues),
            "total_messages": len(self._message_log),
            "queues": {agent_id: queue.qsize() for agent_id, queue in self._queues.items()},
        }

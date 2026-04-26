# knowledge/schema.py
"""Knowledge graph node and edge schema."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any
from uuid import uuid4


class NodeType(Enum):
    """Types of nodes in the knowledge graph."""
    CONCEPT = auto()
    ENTITY = auto()       # Named thing (person, company, product)
    CODE_SYMBOL = auto()  # Function, class, variable
    TOOL = auto()
    SKILL = auto()
    MEMORY = auto()
    GOAL = auto()
    DOCUMENT = auto()


class EdgeType(Enum):
    """Types of edges in the knowledge graph."""
    RELATES_TO = auto()
    DEPENDS_ON = auto()
    CALLS = auto()
    IMPLEMENTS = auto()
    MENTIONED_IN = auto()
    CONTRADICTS = auto()
    SUPPORTS = auto()
    IS_A = auto()
    HAS_PART = auto()


@dataclass
class KGNode:
    """A node in the knowledge graph."""
    node_id: str = field(default_factory=lambda: str(uuid4()))
    node_type: NodeType = NodeType.CONCEPT
    label: str = ""
    properties: dict[str, Any] = field(default_factory=dict)
    embedding: Any = None  # numpy array, set by GraphEngine
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    confidence: float = 1.0


@dataclass
class KGEdge:
    """An edge in the knowledge graph."""
    edge_id: str = field(default_factory=lambda: str(uuid4()))
    source_id: str = ""
    target_id: str = ""
    edge_type: EdgeType = EdgeType.RELATES_TO
    weight: float = 1.0
    properties: dict[str, Any] = field(default_factory=dict)

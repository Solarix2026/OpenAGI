# knowledge/__init__.py
"""Knowledge Graph Engine — semantic graph with GitNexus bridge."""
from knowledge.graph_engine import KnowledgeGraphEngine
from knowledge.schema import KGNode, KGEdge, NodeType, EdgeType
from knowledge.gitnexus_bridge import GitNexusBridge

__all__ = [
    "KnowledgeGraphEngine",
    "KGNode",
    "KGEdge",
    "NodeType",
    "EdgeType",
    "GitNexusBridge",
]

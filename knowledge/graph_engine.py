# knowledge/graph_engine.py
"""Knowledge Graph Engine — semantic graph over agent's world model.

Stores entities, relationships, code symbols, memories, and tools
as a graph queryable by semantic similarity OR graph traversal.

Architecture:
- NetworkX for graph structure (edges, traversal, path-finding)
- FAISS for semantic node lookup (find nodes by text similarity)
- SQLite for persistence (nodes + edges as JSON)

GitNexus compatibility:
- Exposes gitnexus_query(), gitnexus_context(), gitnexus_impact()
- Mountable as MCP server for IDE integration
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

import networkx as nx
import numpy as np
import structlog

from knowledge.schema import KGNode, KGEdge, NodeType, EdgeType
from memory.faiss_store import FaissStore

logger = structlog.get_logger()


class KnowledgeGraphEngine:
    """Semantic knowledge graph with FAISS lookup and NetworkX traversal."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        embedding_dim: int = 384,
    ) -> None:
        self.db_path = db_path or Path(".memory/knowledge_graph.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.graph = nx.DiGraph()
        self.faiss = FaissStore(dim=embedding_dim)
        self._nodes: dict[str, KGNode] = {}
        self._edges: dict[str, KGEdge] = {}

        self._init_db()
        self._load_from_db()

        logger.info("knowledge_graph.initialized", nodes=len(self._nodes))

    def _init_db(self) -> None:
        """Initialize SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS kg_nodes (
                    node_id TEXT PRIMARY KEY,
                    node_type TEXT,
                    label TEXT,
                    properties JSON,
                    confidence REAL,
                    created_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS kg_edges (
                    edge_id TEXT PRIMARY KEY,
                    source_id TEXT,
                    target_id TEXT,
                    edge_type TEXT,
                    weight REAL,
                    properties JSON
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_source ON kg_edges(source_id)")

    def _load_from_db(self) -> None:
        """Load existing graph from SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            for row in conn.execute("SELECT * FROM kg_nodes"):
                node = KGNode(
                    node_id=row[0],
                    node_type=NodeType[row[1]],
                    label=row[2],
                    properties=json.loads(row[3]),
                    confidence=row[4],
                    created_at=row[5],
                )
                self._nodes[node.node_id] = node
                self.graph.add_node(node.node_id, **node.__dict__)
                self.faiss.add(node.node_id, node.label, {"label": node.label})

            for row in conn.execute("SELECT * FROM kg_edges"):
                edge = KGEdge(
                    edge_id=row[0],
                    source_id=row[1],
                    target_id=row[2],
                    edge_type=EdgeType[row[3]],
                    weight=row[4],
                    properties=json.loads(row[5]),
                )
                self._edges[edge.edge_id] = edge
                self.graph.add_edge(
                    edge.source_id, edge.target_id,
                    edge_type=edge.edge_type.name,
                    weight=edge.weight,
                )

    def add_node(self, node: KGNode) -> str:
        """Add a node to the graph."""
        self._nodes[node.node_id] = node
        self.graph.add_node(node.node_id, **node.__dict__)
        self.faiss.add(node.node_id, node.label, {"type": node.node_type.name})

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO kg_nodes VALUES (?, ?, ?, ?, ?, ?)",
                (node.node_id, node.node_type.name, node.label,
                 json.dumps(node.properties), node.confidence, node.created_at),
            )
        return node.node_id

    def add_edge(self, edge: KGEdge) -> str:
        """Add an edge between two nodes."""
        self._edges[edge.edge_id] = edge
        self.graph.add_edge(
            edge.source_id, edge.target_id,
            edge_type=edge.edge_type.name, weight=edge.weight,
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO kg_edges VALUES (?, ?, ?, ?, ?, ?)",
                (edge.edge_id, edge.source_id, edge.target_id,
                 edge.edge_type.name, edge.weight, json.dumps(edge.properties)),
            )
        return edge.edge_id

    def query(self, query_text: str, top_k: int = 5) -> list[KGNode]:
        """Semantic search over nodes."""
        results = self.faiss.query(query_text, top_k=top_k)
        return [
            self._nodes[node_id]
            for node_id, _, _ in results
            if node_id in self._nodes
        ]

    def get_context(self, node_id: str, depth: int = 2) -> dict:
        """Get node + its neighborhood (callers, callees, related nodes)."""
        if node_id not in self.graph:
            return {}

        # BFS up to depth
        neighbors = nx.ego_graph(self.graph, node_id, radius=depth)

        return {
            "node": self._nodes.get(node_id),
            "predecessors": [
                self._nodes[n] for n in self.graph.predecessors(node_id)
                if n in self._nodes
            ],
            "successors": [
                self._nodes[n] for n in self.graph.successors(node_id)
                if n in self._nodes
            ],
            "neighborhood_size": len(neighbors),
        }

    def impact_analysis(self, node_id: str, direction: str = "upstream") -> dict:
        """GitNexus-compatible impact analysis — what does changing this affect?"""
        if node_id not in self.graph:
            return {"blast_radius": 0, "affected": []}

        if direction == "upstream":
            affected = list(nx.ancestors(self.graph, node_id))
        else:
            affected = list(nx.descendants(self.graph, node_id))

        risk_level = "LOW"
        if len(affected) > 20:
            risk_level = "CRITICAL"
        elif len(affected) > 10:
            risk_level = "HIGH"
        elif len(affected) > 5:
            risk_level = "MEDIUM"

        return {
            "blast_radius": len(affected),
            "affected_nodes": affected[:20],
            "risk_level": risk_level,
            "direction": direction,
        }

    def get_stats(self) -> dict:
        """Get graph statistics."""
        return {
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "node_types": {
                nt.name: sum(1 for n in self._nodes.values() if n.node_type == nt)
                for nt in NodeType
            },
        }

# tests/knowledge/test_graph_engine.py
"""Tests for Knowledge Graph Engine - semantic graph with GitNexus bridge."""
import pytest
from knowledge.graph_engine import KnowledgeGraphEngine
from knowledge.schema import KGNode, KGEdge, NodeType, EdgeType
from knowledge.gitnexus_bridge import GitNexusBridge


@pytest.mark.asyncio
async def test_graph_engine_initializes():
    """Test that Knowledge Graph Engine initializes correctly."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_init.db"
        graph = KnowledgeGraphEngine(db_path=db_path)
        assert graph is not None
        assert len(graph._nodes) == 0
        assert len(graph._edges) == 0


@pytest.mark.asyncio
async def test_graph_engine_adds_node():
    """Test adding a node to the graph."""
    graph = KnowledgeGraphEngine()

    node = KGNode(
        node_type=NodeType.CONCEPT,
        label="REST API",
        properties={"description": "Representational State Transfer API"}
    )

    node_id = graph.add_node(node)
    assert node_id == node.node_id
    assert len(graph._nodes) == 1


@pytest.mark.asyncio
async def test_graph_engine_adds_edge():
    """Test adding an edge between nodes."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_add_edge.db"
        graph = KnowledgeGraphEngine(db_path=db_path)

        node1 = KGNode(node_type=NodeType.CONCEPT, label="API")
        node2 = KGNode(node_type=NodeType.CONCEPT, label="REST")

        graph.add_node(node1)
        graph.add_node(node2)

        edge = KGEdge(
            source_id=node1.node_id,
            target_id=node2.node_id,
            edge_type=EdgeType.IS_A
        )

        edge_id = graph.add_edge(edge)
        assert edge_id == edge.edge_id
        assert len(graph._edges) == 1


@pytest.mark.asyncio
async def test_graph_engine_queries_by_text():
    """Test semantic search over nodes."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_query.db"
        graph = KnowledgeGraphEngine(db_path=db_path)

        node = KGNode(
            node_type=NodeType.CONCEPT,
            label="Machine Learning",
            properties={"domain": "AI"}
        )

        graph.add_node(node)

        results = graph.query("machine learning", top_k=5)
        assert len(results) > 0
        assert results[0].label == "Machine Learning"


@pytest.mark.asyncio
async def test_graph_engine_gets_context():
    """Test getting node context (neighbors)."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_context.db"
        graph = KnowledgeGraphEngine(db_path=db_path)

        node1 = KGNode(node_type=NodeType.CONCEPT, label="API")
        node2 = KGNode(node_type=NodeType.CONCEPT, label="REST")
        node3 = KGNode(node_type=NodeType.CONCEPT, label="GraphQL")

        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_node(node3)

        graph.add_edge(KGEdge(source_id=node1.node_id, target_id=node2.node_id, edge_type=EdgeType.IS_A))
        graph.add_edge(KGEdge(source_id=node1.node_id, target_id=node3.node_id, edge_type=EdgeType.IS_A))

        context = graph.get_context(node1.node_id, depth=1)
        assert context["node"] is not None
        assert len(context["successors"]) == 2


@pytest.mark.asyncio
async def test_graph_engine_impact_analysis():
    """Test impact analysis for a node."""
    graph = KnowledgeGraphEngine()

    node1 = KGNode(node_type=NodeType.CODE_SYMBOL, label="function_a")
    node2 = KGNode(node_type=NodeType.CODE_SYMBOL, label="function_b")
    node3 = KGNode(node_type=NodeType.CODE_SYMBOL, label="function_c")

    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_node(node3)

    # Create dependency chain: c -> b -> a
    graph.add_edge(KGEdge(source_id=node3.node_id, target_id=node2.node_id, edge_type=EdgeType.CALLS))
    graph.add_edge(KGEdge(source_id=node2.node_id, target_id=node1.node_id, edge_type=EdgeType.CALLS))

    impact = graph.impact_analysis(node1.node_id, direction="upstream")
    assert impact["blast_radius"] == 2
    assert impact["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


@pytest.mark.asyncio
async def test_gitnexus_bridge_query():
    """Test GitNexus bridge query method."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_bridge_query.db"
        graph = KnowledgeGraphEngine(db_path=db_path)

        node = KGNode(
            node_type=NodeType.CODE_SYMBOL,
            label="calculate_total",
            properties={"type": "function"}
        )

        graph.add_node(node)

        bridge = GitNexusBridge(graph)
        result = await bridge.gitnexus_query("calculate total")

        assert result["query"] == "calculate total"
        assert len(result["results"]) > 0


@pytest.mark.asyncio
async def test_gitnexus_bridge_context():
    """Test GitNexus bridge context method."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_context.db"
        graph = KnowledgeGraphEngine(db_path=db_path)

        node = KGNode(
            node_type=NodeType.CODE_SYMBOL,
            label="main_function_unique",
            properties={"type": "function"}
        )

        graph.add_node(node)

        bridge = GitNexusBridge(graph)
        result = await bridge.gitnexus_context("main_function_unique")

        assert result["node"]["label"] == "main_function_unique"
        assert result["node"]["type"] == "CODE_SYMBOL"


@pytest.mark.asyncio
async def test_gitnexus_bridge_impact():
    """Test GitNexus bridge impact method."""
    graph = KnowledgeGraphEngine()

    node = KGNode(
        node_type=NodeType.CODE_SYMBOL,
        label="critical_function",
        properties={"type": "function"}
    )

    graph.add_node(node)

    bridge = GitNexusBridge(graph)
    result = await bridge.gitnexus_impact("critical_function", direction="upstream")

    assert "blast_radius" in result
    assert "risk_level" in result


@pytest.mark.asyncio
async def test_gitnexus_bridge_detect_changes():
    """Test GitNexus bridge detect_changes method."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_bridge_detect.db"
        graph = KnowledgeGraphEngine(db_path=db_path)

        bridge = GitNexusBridge(graph)
        result = await bridge.gitnexus_detect_changes()

        assert result["status"] == "ok"
        assert "graph_stats" in result


@pytest.mark.asyncio
async def test_graph_engine_gets_stats():
    """Test getting graph statistics."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_stats.db"
        graph = KnowledgeGraphEngine(db_path=db_path)

        node1 = KGNode(node_type=NodeType.CONCEPT, label="API")
        node2 = KGNode(node_type=NodeType.TOOL, label="web_search")

        graph.add_node(node1)
        graph.add_node(node2)

        stats = graph.get_stats()
        assert stats["nodes"] == 2
        assert stats["edges"] == 0
        assert "node_types" in stats


@pytest.mark.asyncio
async def test_graph_engine_persistence():
    """Test that graph persists to SQLite."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_graph.db"
        graph1 = KnowledgeGraphEngine(db_path=db_path)

        node = KGNode(
            node_type=NodeType.CONCEPT,
            label="Test Concept"
        )

        graph1.add_node(node)

        # Create new instance with same DB
        graph2 = KnowledgeGraphEngine(db_path=db_path)

        # Should have loaded the node
        assert len(graph2._nodes) == 1
        assert "Test Concept" in [n.label for n in graph2._nodes.values()]


@pytest.mark.asyncio
async def test_graph_engine_multiple_node_types():
    """Test handling multiple node types."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_types.db"
        graph = KnowledgeGraphEngine(db_path=db_path)

        nodes = [
            KGNode(node_type=NodeType.CONCEPT, label="Concept"),
            KGNode(node_type=NodeType.ENTITY, label="Entity"),
            KGNode(node_type=NodeType.CODE_SYMBOL, label="Function"),
            KGNode(node_type=NodeType.TOOL, label="Tool"),
        ]

        for node in nodes:
            graph.add_node(node)

        stats = graph.get_stats()
        assert stats["nodes"] == 4
        assert stats["node_types"]["CONCEPT"] == 1
        assert stats["node_types"]["ENTITY"] == 1
        assert stats["node_types"]["CODE_SYMBOL"] == 1
        assert stats["node_types"]["TOOL"] == 1

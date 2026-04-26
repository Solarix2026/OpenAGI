# tests/api/test_server.py
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from api.server import create_app
from config.settings import Settings


@pytest.fixture
def mock_settings():
    settings = Settings()
    return settings


@pytest.fixture
def mock_kernel():
    kernel = AsyncMock()
    kernel.registry = AsyncMock()
    kernel.registry.list_tools = AsyncMock(return_value=[])
    kernel.skill_loader = AsyncMock()
    kernel.skill_loader.list_skills = AsyncMock(return_value=[])
    kernel.memory = AsyncMock()
    return kernel


@pytest.fixture
def client(mock_settings, mock_kernel):
    app = create_app(settings=mock_settings, kernel=mock_kernel)
    return TestClient(app)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"


def test_tools_endpoint(client, mock_kernel):
    # Mock tools
    from tools.base_tool import ToolMeta
    mock_tool = ToolMeta(
        name="test_tool",
        description="Test tool",
        parameters={"type": "object"},
        risk_score=0.1,
        categories=["test"],
    )
    mock_kernel.registry.list_tools = lambda: [mock_tool]

    response = client.get("/tools")
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    assert len(data["tools"]) >= 1
    assert data["tools"][0]["name"] == "test_tool"


def test_skills_endpoint(client, mock_kernel):
    # Mock skills
    from skills.__loader__ import SkillMeta
    mock_skill = SkillMeta(
        name="test_skill",
        version="1.0.0",
        capabilities=["test"],
        tools_required=[],
        telos_alignment=0.9,
        body="Test skill",
    )
    mock_kernel.skill_loader.list_skills = lambda: [mock_skill]

    response = client.get("/skills")
    assert response.status_code == 200
    data = response.json()
    assert "skills" in data
    assert len(data["skills"]) >= 1
    assert data["skills"][0]["name"] == "test_skill"


def test_memory_recall_endpoint(client, mock_kernel):
    # Mock memory recall
    from memory.memory_core import MemoryItem
    mock_item = MemoryItem(
        id="test-id",
        content="Test memory",
        layer=mock_kernel.memory.WORKING,
        confidence_score=0.9,
        created_at=None,
        metadata={},
    )
    mock_kernel.memory.recall = AsyncMock(return_value=[mock_item])

    response = client.post("/memory/recall", json={"query": "test", "layer": "working"})
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) >= 1


def test_memory_recall_with_invalid_layer(client, mock_kernel):
    mock_kernel.memory.recall = AsyncMock(return_value=[])

    response = client.post("/memory/recall", json={"query": "test", "layer": "invalid"})
    assert response.status_code == 200  # Should default to working layer


def test_memory_recall_without_query(client, mock_kernel):
    mock_kernel.memory.recall = AsyncMock(return_value=[])

    response = client.post("/memory/recall", json={"layer": "working"})
    assert response.status_code == 200


def test_websocket_connection(client):
    # Note: TestClient doesn't support WebSocket testing well
    # This is a placeholder for future WebSocket tests
    pass


def test_cors_middleware(client):
    response = client.options("/health", headers={"Origin": "http://example.com"})
    # Check that CORS headers are present
    assert "access-control-allow-origin" in response.headers


def test_tools_endpoint_empty(client, mock_kernel):
    mock_kernel.registry.list_tools = lambda: []

    response = client.get("/tools")
    assert response.status_code == 200
    data = response.json()
    assert data["tools"] == []


def test_skills_endpoint_empty(client, mock_kernel):
    mock_kernel.skill_loader.list_skills = lambda: []

    response = client.get("/skills")
    assert response.status_code == 200
    data = response.json()
    assert data["skills"] == []


def test_memory_recall_empty_results(client, mock_kernel):
    mock_kernel.memory.recall = AsyncMock(return_value=[])

    response = client.post("/memory/recall", json={"query": "nonexistent", "layer": "working"})
    assert response.status_code == 200
    data = response.json()
    assert data["results"] == []


def test_health_endpoint_includes_agent_info(client, mock_settings):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "agent" in data


def test_tools_endpoint_includes_risk_score(client, mock_kernel):
    from tools.base_tool import ToolMeta
    mock_tool = ToolMeta(
        name="risky_tool",
        description="Risky tool",
        parameters={"type": "object"},
        risk_score=0.8,
        categories=["test"],
    )
    mock_kernel.registry.list_tools = lambda: [mock_tool]

    response = client.get("/tools")
    assert response.status_code == 200
    data = response.json()
    assert data["tools"][0]["risk"] == 0.8


def test_skills_endpoint_includes_capabilities(client, mock_kernel):
    from skills.__loader__ import SkillMeta
    mock_skill = SkillMeta(
        name="capable_skill",
        version="1.0.0",
        capabilities=["capability1", "capability2"],
        tools_required=[],
        telos_alignment=0.9,
        body="Test",
    )
    mock_kernel.skill_loader.list_skills = lambda: [mock_skill]

    response = client.get("/skills")
    assert response.status_code == 200
    data = response.json()
    assert "capability1" in data["skills"][0]["capabilities"]


def test_memory_recall_includes_confidence(client, mock_kernel):
    from memory.memory_core import MemoryItem
    mock_item = MemoryItem(
        id="test-id",
        content="Test",
        layer=mock_kernel.memory.WORKING,
        confidence_score=0.95,
        created_at=None,
        metadata={},
    )
    mock_kernel.memory.recall = AsyncMock(return_value=[mock_item])

    response = client.post("/memory/recall", json={"query": "test", "layer": "working"})
    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["confidence"] == 0.95


def test_404_on_unknown_endpoint(client):
    response = client.get("/unknown")
    assert response.status_code == 404


def test_memory_recall_with_top_k(client, mock_kernel):
    from memory.memory_core import MemoryItem
    mock_items = [
        MemoryItem(
            id=f"id-{i}",
            content=f"Memory {i}",
            layer=mock_kernel.memory.WORKING,
            confidence_score=0.9 - (i * 0.1),
            created_at=None,
            metadata={},
        )
        for i in range(5)
    ]
    mock_kernel.memory.recall = AsyncMock(return_value=mock_items[:3])

    response = client.post("/memory/recall", json={"query": "test", "layer": "working", "top_k": 3})
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 3

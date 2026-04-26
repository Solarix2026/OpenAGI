# tests/tools/builtin/test_skill_tool.py
import pytest
from unittest.mock import AsyncMock
from tools.builtin.skill_tool import SkillTool
from skills.skill_loader import SkillLoader, SkillMeta


@pytest.fixture
def skill_loader():
    loader = SkillLoader()
    # Add a test skill
    skill = SkillMeta(
        name="test_skill",
        version="1.0.0",
        capabilities=["test"],
        tools_required=[],
        telos_alignment=0.9,
        body="Test skill body",
    )
    loader._skills["test_skill"] = skill
    return loader


@pytest.mark.asyncio
async def test_list_skills(skill_loader):
    tool = SkillTool(loader=skill_loader)
    result = await tool.execute(action="list")
    assert result.success
    assert "skills" in result.data
    assert len(result.data["skills"]) >= 1
    assert result.data["skills"][0]["name"] == "test_skill"


@pytest.mark.asyncio
async def test_load_skill(skill_loader):
    tool = SkillTool(loader=skill_loader)
    result = await tool.execute(action="load", skill_name="test_skill")
    assert result.success
    assert result.data["loaded"] == "test_skill"


@pytest.mark.asyncio
async def test_invoke_skill(skill_loader):
    tool = SkillTool(loader=skill_loader)

    # Mock LLM for skill invocation
    skill_loader.llm = AsyncMock()

    async def mock_stream(req):
        yield "Skill"
        yield " output"

    skill_loader.llm.stream = mock_stream

    result = await tool.execute(
        action="invoke",
        skill_name="test_skill",
        context={"input": "test"},
    )

    assert result.success
    assert "output" in result.data
    assert "Skill output" in result.data["output"]


@pytest.mark.asyncio
async def test_install_skill_from_github(skill_loader):
    tool = SkillTool(loader=skill_loader)

    # Mock GitHub fetch
    import httpx
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = """---
name: github_skill
version: 1.0.0
capabilities: [github]
tools_required: []
telos_alignment: 0.9
---
# GitHub Skill
"""

    with patch('skills.__loader__.httpx.get', return_value=mock_response):
        result = await tool.execute(
            action="install",
            github_url="https://github.com/test/skill.md",
        )

    assert result.success
    assert result.data["installed"] == "github_skill"


@pytest.mark.asyncio
async def test_skill_tool_without_loader():
    tool = SkillTool(loader=None)
    result = await tool.execute(action="list")
    assert not result.success
    assert "not attached" in result.error.lower()


@pytest.mark.asyncio
async def test_unknown_action(skill_loader):
    tool = SkillTool(loader=skill_loader)
    result = await tool.execute(action="unknown")
    assert not result.success
    assert "unknown" in result.error.lower()


@pytest.mark.asyncio
async def test_skill_tool_metadata():
    tool = SkillTool()
    assert tool.meta.name == "skill"
    assert "action" in tool.meta.parameters["properties"]
    assert "list" in tool.meta.parameters["properties"]["action"]["enum"]
    assert "load" in tool.meta.parameters["properties"]["action"]["enum"]
    assert "invoke" in tool.meta.parameters["properties"]["action"]["enum"]
    assert "install" in tool.meta.parameters["properties"]["action"]["enum"]
    assert tool.meta.risk_score == 0.2


@pytest.mark.asyncio
async def test_invoke_skill_with_context(skill_loader):
    tool = SkillTool(loader=skill_loader)

    skill_loader.llm = AsyncMock()

    async def mock_stream(req):
        # Check that context is passed
        assert "context" in req.system or "context" in str(req.messages)
        yield "Processed"

    skill_loader.llm.stream = mock_stream

    result = await tool.execute(
        action="invoke",
        skill_name="test_skill",
        context={"key": "value", "data": 123},
    )

    assert result.success


@pytest.mark.asyncio
async def test_invoke_nonexistent_skill(skill_loader):
    tool = SkillTool(loader=skill_loader)
    skill_loader.llm = AsyncMock()

    result = await tool.execute(
        action="invoke",
        skill_name="nonexistent_skill",
        context={},
    )

    assert not result.success
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_load_nonexistent_skill(skill_loader):
    tool = SkillTool(loader=skill_loader)
    result = await tool.execute(action="load", skill_name="nonexistent")
    assert not result.success


@pytest.mark.asyncio
async def test_install_handles_github_error(skill_loader):
    tool = SkillTool(loader=skill_loader)

    with patch('skills.__loader__.httpx.get', side_effect=Exception("Network error")):
        result = await tool.execute(
            action="install",
            github_url="https://github.com/test/skill.md",
        )

    assert not result.success


@pytest.mark.asyncio
async def test_list_empty_skills():
    empty_loader = SkillLoader()
    tool = SkillTool(loader=empty_loader)
    result = await tool.execute(action="list")
    assert result.success
    assert len(result.data["skills"]) == 0

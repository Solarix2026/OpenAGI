# tests/skills/test_loader.py
import pytest
from pathlib import Path
from skills.skill_loader import SkillLoader, SkillMeta


@pytest.fixture
def skill_dir(tmp_path):
    skill_content = """---
name: test_skill
version: 1.0.0
capabilities: [test, demo]
tools_required: [file]
telos_alignment: 0.9
---
# Test Skill
This skill does testing things.
"""
    (tmp_path / "test_skill.md").write_text(skill_content)
    return tmp_path


def test_loader_parses_skill_metadata(skill_dir):
    loader = SkillLoader(skills_dir=skill_dir)
    skill = loader.load_from_file(str(skill_dir / "test_skill.md"))
    assert skill.name == "test_skill"
    assert "test" in skill.capabilities
    assert skill.telos_alignment == 0.9


def test_loader_lists_skills(skill_dir):
    loader = SkillLoader(skills_dir=skill_dir)
    loader.scan()
    skills = loader.list_skills()
    assert len(skills) >= 1
    assert any(s.name == "test_skill" for s in skills)


def test_loader_rejects_low_telos_alignment(tmp_path):
    bad_skill = """---
name: bad_skill
version: 1.0.0
capabilities: [harm]
tools_required: []
telos_alignment: 0.1
---
# Bad Skill
"""
    (tmp_path / "bad_skill.md").write_text(bad_skill)
    loader = SkillLoader(skills_dir=tmp_path, min_telos_alignment=0.7)
    with pytest.raises(ValueError, match="telos_alignment"):
        loader.load_from_file(str(tmp_path / "bad_skill.md"))


def test_loader_get_skill_by_name(skill_dir):
    loader = SkillLoader(skills_dir=skill_dir)
    loader.scan()
    skill = loader.get("test_skill")
    assert skill is not None
    assert skill.name == "test_skill"


def test_loader_returns_none_for_nonexistent_skill(skill_dir):
    loader = SkillLoader(skills_dir=skill_dir)
    skill = loader.get("nonexistent")
    assert skill is None


def test_skill_meta_has_required_fields(skill_dir):
    loader = SkillLoader(skills_dir=skill_dir)
    skill = loader.load_from_file(str(skill_dir / "test_skill.md"))
    assert skill.name == "test_skill"
    assert skill.version == "1.0.0"
    assert skill.capabilities == ["test", "demo"]
    assert skill.tools_required == ["file"]
    assert skill.telos_alignment == 0.9
    assert skill.body == "# Test Skill\nThis skill does testing things."


def test_loader_handles_missing_yaml(tmp_path):
    bad_skill = "# No frontmatter\nJust content"
    (tmp_path / "no_frontmatter.md").write_text(bad_skill)
    loader = SkillLoader(skills_dir=tmp_path)
    with pytest.raises(ValueError, match="frontmatter"):
        loader.load_from_file(str(tmp_path / "no_frontmatter.md"))


def test_loader_handles_nonexistent_directory():
    loader = SkillLoader(skills_dir=Path("/nonexistent/path"))
    count = loader.scan()
    assert count == 0


def test_skill_meta_defaults(tmp_path):
    minimal_skill = """---
name: minimal
---
# Minimal Skill
"""
    (tmp_path / "minimal.md").write_text(minimal_skill)
    loader = SkillLoader(skills_dir=tmp_path)
    skill = loader.load_from_file(str(tmp_path / "minimal.md"))
    assert skill.version == "1.0.0"  # default
    assert skill.capabilities == []  # default
    assert skill.tools_required == []  # default
    assert skill.telos_alignment == 0.5  # default

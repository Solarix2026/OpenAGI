# tests/tools/builtin/test_file_tool.py
import pytest
import tempfile
import os
from pathlib import Path
from tools.builtin.file_tool import FileTool


@pytest.fixture
def tmp(tmp_path):
    return tmp_path


@pytest.mark.asyncio
async def test_write_and_read_file(tmp):
    tool = FileTool(base_dir=tmp)
    await tool.execute(action="write", path=str(tmp / "test.txt"), content="hello")
    result = await tool.execute(action="read", path=str(tmp / "test.txt"))
    assert result.success
    assert result.data["content"] == "hello"


@pytest.mark.asyncio
async def test_list_directory(tmp):
    (tmp / "a.py").write_text("x")
    (tmp / "b.py").write_text("y")
    tool = FileTool(base_dir=tmp)
    result = await tool.execute(action="list", path=str(tmp))
    assert result.success
    assert len(result.data["files"]) >= 2


@pytest.mark.asyncio
async def test_mkdir(tmp):
    tool = FileTool(base_dir=tmp)
    result = await tool.execute(action="mkdir", path=str(tmp / "subdir"))
    assert result.success
    assert (tmp / "subdir").is_dir()


@pytest.mark.asyncio
async def test_str_replace(tmp):
    """Surgical file editing — not full rewrite."""
    p = tmp / "code.py"
    p.write_text("def foo():\n    return 1\n")
    tool = FileTool(base_dir=tmp)
    result = await tool.execute(
        action="str_replace",
        path=str(p),
        old_str="return 1",
        new_str="return 2",
    )
    assert result.success
    assert p.read_text() == "def foo():\n    return 2\n"


@pytest.mark.asyncio
async def test_path_traversal_blocked(tmp):
    """Cannot escape base_dir."""
    tool = FileTool(base_dir=tmp)
    result = await tool.execute(action="read", path="/etc/passwd")
    assert not result.success
    assert "outside" in result.error.lower() or "blocked" in result.error.lower()


@pytest.mark.asyncio
async def test_delete_file(tmp):
    p = tmp / "to_delete.txt"
    p.write_text("content")
    tool = FileTool(base_dir=tmp)
    result = await tool.execute(action="delete", path=str(p))
    assert result.success
    assert not p.exists()


@pytest.mark.asyncio
async def test_delete_directory(tmp):
    d = tmp / "to_delete"
    d.mkdir()
    (d / "file.txt").write_text("content")
    tool = FileTool(base_dir=tmp)
    result = await tool.execute(action="delete", path=str(d))
    assert result.success
    assert not d.exists()


@pytest.mark.asyncio
async def test_exists_file(tmp):
    p = tmp / "exists.txt"
    p.write_text("content")
    tool = FileTool(base_dir=tmp)
    result = await tool.execute(action="exists", path=str(p))
    assert result.success
    assert result.data["exists"] is True
    assert result.data["is_dir"] is False


@pytest.mark.asyncio
async def test_exists_directory(tmp):
    d = tmp / "exists_dir"
    d.mkdir()
    tool = FileTool(base_dir=tmp)
    result = await tool.execute(action="exists", path=str(d))
    assert result.success
    assert result.data["exists"] is True
    assert result.data["is_dir"] is True


@pytest.mark.asyncio
async def test_exists_nonexistent(tmp):
    tool = FileTool(base_dir=tmp)
    result = await tool.execute(action="exists", path=str(tmp / "nonexistent"))
    assert result.success
    assert result.data["exists"] is False


@pytest.mark.asyncio
async def test_str_replace_requires_old_str(tmp):
    tool = FileTool(base_dir=tmp)
    result = await tool.execute(
        action="str_replace",
        path=str(tmp / "test.txt"),
        new_str="new",
    )
    assert not result.success
    assert "old_str" in result.error.lower()


@pytest.mark.asyncio
async def test_str_replace_fails_if_not_found(tmp):
    p = tmp / "code.py"
    p.write_text("def foo():\n    return 1\n")
    tool = FileTool(base_dir=tmp)
    result = await tool.execute(
        action="str_replace",
        path=str(p),
        old_str="return 2",
        new_str="return 3",
    )
    assert not result.success
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_str_replace_fails_if_multiple_occurrences(tmp):
    p = tmp / "code.py"
    p.write_text("x = 1\nx = 1\n")
    tool = FileTool(base_dir=tmp)
    result = await tool.execute(
        action="str_replace",
        path=str(p),
        old_str="x = 1",
        new_str="x = 2",
    )
    assert not result.success
    assert "appears" in result.error.lower() or "times" in result.error.lower()


@pytest.mark.asyncio
async def test_write_creates_parent_directories(tmp):
    tool = FileTool(base_dir=tmp)
    result = await tool.execute(
        action="write",
        path=str(tmp / "deep" / "nested" / "file.txt"),
        content="content",
    )
    assert result.success
    assert (tmp / "deep" / "nested" / "file.txt").exists()


@pytest.mark.asyncio
async def test_unknown_action(tmp):
    tool = FileTool(base_dir=tmp)
    result = await tool.execute(action="unknown", path=str(tmp / "test.txt"))
    assert not result.success
    assert "unknown" in result.error.lower()


@pytest.mark.asyncio
async def test_file_tool_metadata():
    tool = FileTool()
    assert tool.meta.name == "file"
    assert "read" in tool.meta.parameters["properties"]["action"]["enum"]
    assert "write" in tool.meta.parameters["properties"]["action"]["enum"]
    assert tool.meta.risk_score == 0.3

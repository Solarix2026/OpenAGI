# tests/test_simple.py
"""Simple test to check pytest functionality."""
import sys
import os

def test_python_path():
    """Test that Python path is set correctly."""
    # Check if project root is in path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert project_root in sys.path, f"Project root {project_root} not in Python path"
    print(f"Project root: {project_root}")
    print(f"Python path: {sys.path[:5]}")

def test_skills_directory_exists():
    """Test that skills directory exists."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    skills_dir = os.path.join(project_root, "skills")
    assert os.path.exists(skills_dir), f"Skills directory {skills_dir} does not exist"
    assert os.path.isfile(os.path.join(skills_dir, "skill_loader.py")), "skill_loader.py not found"
    print(f"Skills directory: {skills_dir}")

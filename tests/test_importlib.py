# tests/test_importlib.py
"""Test import using importlib."""
import sys
import os
import importlib.util

def test_import_with_importlib():
    """Test importing skills.skill_loader using importlib."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    skills_path = os.path.join(project_root, "skills", "skill_loader.py")

    print(f"Project root: {project_root}")
    print(f"Skills path: {skills_path}")
    print(f"File exists: {os.path.exists(skills_path)}")

    spec = importlib.util.spec_from_file_location("skills.skill_loader", skills_path)
    if spec is None:
        print("Spec is None!")
        return

    print(f"Spec: {spec}")
    print(f"Spec loader: {spec.loader}")

    module = importlib.util.module_from_spec(spec)
    sys.modules["skills.skill_loader"] = module

    if spec.loader:
        spec.loader.exec_module(module)

    print(f"Module loaded: {module}")
    print(f"Module dir: {dir(module)}")

    # Try to get the classes
    SkillLoader = getattr(module, "SkillLoader", None)
    SkillMeta = getattr(module, "SkillMeta", None)

    print(f"SkillLoader: {SkillLoader}")
    print(f"SkillMeta: {SkillMeta}")

    assert SkillLoader is not None, "SkillLoader not found"
    assert SkillMeta is not None, "SkillMeta not found"

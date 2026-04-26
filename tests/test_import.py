# tests/test_import.py
"""Test import of skills module."""
import sys
print("Python path:", sys.path[:5])

try:
    from skills.skill_loader import SkillLoader, SkillMeta
    print("Import successful!")
    print("SkillLoader:", SkillLoader)
    print("SkillMeta:", SkillMeta)
except ImportError as e:
    print("Import failed:", e)
    print("Current directory:", __file__)

# skills/__init__.py
"""Skills components for OpenAGI v5."""
# Removed direct imports to avoid circular dependency issues
# Import directly: from skills.skill_loader import SkillLoader, SkillMeta

__all__ = [
    "SkillLoader",
    "SkillMeta",
]

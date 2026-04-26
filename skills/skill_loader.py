# skills/skill_loader.py
"""Skill loader for OpenAGI v5.

Loads skills from markdown files with YAML frontmatter.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import structlog

from core.telos_core import TelosCore

logger = structlog.get_logger()


class SkillStatus(Enum):
    """Status of a skill."""
    LOADED = "loaded"
    UNLOADED = "unloaded"
    ERROR = "error"


@dataclass(frozen=True)
class Skill:
    """A loaded skill."""
    name: str
    description: str
    path: Path
    telos_aligned: bool
    metadata: dict[str, Any] = field(default_factory=dict)
    content: str = ""
    loaded_at: datetime = field(default_factory=datetime.utcnow)


class SkillLoader:
    """
    Load and manage skills from markdown files.

    Skills are markdown files with YAML frontmatter.
    Validates against Telos before loading.
    """

    def __init__(self, telos: Optional[TelosCore] = None):
        self.telos = telos
        self._loaded_skills: dict[str, Skill] = {}
        logger.info("skill.loader.initialized")

    async def load_skill(self, path: Path) -> Optional[Skill]:
        """Load a skill from a markdown file."""
        try:
            if not path.exists():
                logger.error("skill.loader.not_found", path=str(path))
                return None

            # Read file
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse YAML frontmatter
            metadata = {}
            skill_content = content

            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 2:
                    try:
                        import yaml
                        metadata = yaml.safe_load(parts[1]) or {}
                        skill_content = parts[2] if len(parts) > 2 else ""
                    except ImportError:
                        # Fallback: simple parsing
                        frontmatter = parts[1]
                        for line in frontmatter.split("\n"):
                            if ":" in line:
                                key, value = line.split(":", 1)
                                metadata[key.strip()] = value.strip()
                        skill_content = parts[2] if len(parts) > 2 else ""

            # Extract skill info
            name = metadata.get("name", path.stem)
            description = metadata.get("description", "")

            # Validate against Telos
            telos_aligned = True
            if self.telos:
                drift = self.telos.drift_score(description + " " + skill_content)
                telos_aligned = drift < 0.7

                if not telos_aligned:
                    logger.warning(
                        "skill.loader.telos_misaligned",
                        name=name,
                        drift=drift
                    )

            # Create skill
            skill = Skill(
                name=name,
                description=description,
                path=path,
                telos_aligned=telos_aligned,
                metadata=metadata,
                content=skill_content
            )

            # Store skill
            self._loaded_skills[str(path)] = skill

            logger.info("skill.loader.loaded", name=name, path=str(path))
            return skill

        except Exception as e:
            logger.exception("skill.loader.error", path=str(path), error=str(e))
            return None

    async def unload_skill(self, path: str) -> bool:
        """Unload a skill."""
        if path in self._loaded_skills:
            skill = self._loaded_skills[path]
            del self._loaded_skills[path]
            logger.info("skill.loader.unloaded", name=skill.name, path=path)
            return True
        return False

    async def validate_skill(self, path: Path) -> tuple[bool, list[str]]:
        """Validate a skill file."""
        issues = []

        if not path.exists():
            issues.append(f"File not found: {path}")
            return False, issues

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for YAML frontmatter
            if not content.startswith("---"):
                issues.append("Missing YAML frontmatter (should start with ---)")

            # Check for required fields
            if "---" in content:
                parts = content.split("---", 2)
                if len(parts) >= 2:
                    try:
                        import yaml
                        metadata = yaml.safe_load(parts[1]) or {}
                    except ImportError:
                        metadata = {}

                    if "name" not in metadata:
                        issues.append("Missing required field: name")
                    if "description" not in metadata:
                        issues.append("Missing required field: description")

            # Validate against Telos
            if self.telos:
                drift = self.telos.drift_score(content)
                if drift >= 0.7:
                    issues.append(f"Telos misalignment detected (drift: {drift:.2f})")

            return len(issues) == 0, issues

        except Exception as e:
            issues.append(f"Validation error: {str(e)}")
            return False, issues

    def list_loaded_skills(self) -> list[Skill]:
        """List all loaded skills."""
        return list(self._loaded_skills.values())

    def get_skill(self, path: str) -> Optional[Skill]:
        """Get a loaded skill by path."""
        return self._loaded_skills.get(path)

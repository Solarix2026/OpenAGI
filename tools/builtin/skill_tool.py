# tools/builtin/skill_tool.py
"""Skill management tool.

Load, unload, and list skills from markdown files.
"""
from pathlib import Path
from typing import Any

import structlog

from tools.base_tool import BaseTool, ToolMeta, ToolResult
from skills.skill_loader import SkillLoader
from core.telos_core import TelosCore

logger = structlog.get_logger()


class SkillTool(BaseTool):
    """
    Manage skills from markdown files.

    - Load skills from markdown
    - Unload skills
    - List available skills
    - Validate against Telos
    """

    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="skill",
            description="Load, unload, and list skills from markdown files",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["load", "unload", "list", "validate"],
                        "description": "Skill action to perform"
                    },
                    "skill_path": {
                        "type": "string",
                        "description": "Path to skill markdown file (for load/unload)"
                    },
                    "skills_dir": {
                        "type": "string",
                        "description": "Directory containing skills (for list action)"
                    }
                },
                "required": ["action"]
            },
            risk_score=0.3,
            categories=["skills", "management"],
            examples=[
                {
                    "action": "load",
                    "skill_path": "/path/to/skill.md"
                },
                {
                    "action": "list",
                    "skills_dir": "/path/to/skills"
                }
            ]
        )

    def __init__(self, skill_loader: SkillLoader = None, telos: TelosCore = None):
        super().__init__()
        self.skill_loader = skill_loader
        self.telos = telos

    async def execute(self, **kwargs) -> ToolResult:
        """Execute skill operation."""
        import time
        start_time = time.time()

        action = kwargs.get("action", "")

        if not action:
            return ToolResult(
                success=False,
                tool_name=self.meta.name,
                error="No action provided"
            )

        try:
            if action == "load":
                skill_path_str = kwargs.get("skill_path", "")

                if not skill_path_str:
                    return ToolResult(
                        success=False,
                        tool_name=self.meta.name,
                        error="No skill path provided"
                    )

                skill_path = Path(skill_path_str)

                if not skill_path.exists():
                    return ToolResult(
                        success=False,
                        tool_name=self.meta.name,
                        error=f"Skill file not found: {skill_path_str}"
                    )

                # Load skill
                if self.skill_loader is None:
                    self.skill_loader = SkillLoader(telos=self.telos)

                skill = await self.skill_loader.load_skill(skill_path)

                if skill is None:
                    return ToolResult(
                        success=False,
                        tool_name=self.meta.name,
                        error=f"Failed to load skill: {skill_path_str}"
                    )

                return ToolResult(
                    success=True,
                    tool_name=self.meta.name,
                    data=f"Loaded skill: {skill.name}",
                    execution_time_ms=(time.time() - start_time) * 1000,
                    metadata={
                        "skill_name": skill.name,
                        "skill_path": str(skill_path),
                        "description": skill.description
                    }
                )

            elif action == "unload":
                skill_path_str = kwargs.get("skill_path", "")

                if not skill_path_str:
                    return ToolResult(
                        success=False,
                        tool_name=self.meta.name,
                        error="No skill path provided"
                    )

                if self.skill_loader is None:
                    return ToolResult(
                        success=False,
                        tool_name=self.meta.name,
                        error="Skill loader not initialized"
                    )

                success = await self.skill_loader.unload_skill(skill_path_str)

                if success:
                    return ToolResult(
                        success=True,
                        tool_name=self.meta.name,
                        data=f"Unloaded skill: {skill_path_str}",
                        execution_time_ms=(time.time() - start_time) * 1000
                    )
                else:
                    return ToolResult(
                        success=False,
                        tool_name=self.meta.name,
                        error=f"Failed to unload skill: {skill_path_str}"
                    )

            elif action == "list":
                skills_dir_str = kwargs.get("skills_dir", "skills/builtin")

                skills_dir = Path(skills_dir_str)

                if not skills_dir.exists():
                    return ToolResult(
                        success=False,
                        tool_name=self.meta.name,
                        error=f"Skills directory not found: {skills_dir_str}"
                    )

                # List all markdown files
                skill_files = list(skills_dir.glob("*.md"))

                skills = []
                for skill_file in skill_files:
                    # Try to load metadata
                    if self.skill_loader is None:
                        self.skill_loader = SkillLoader(telos=self.telos)

                    skill = await self.skill_loader.load_skill(skill_file)
                    if skill:
                        skills.append({
                            "name": skill.name,
                            "path": str(skill_file),
                            "description": skill.description,
                            "telos_aligned": skill.telos_aligned
                        })

                return ToolResult(
                    success=True,
                    tool_name=self.meta.name,
                    data=skills,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    metadata={"count": len(skills), "directory": str(skills_dir)}
                )

            elif action == "validate":
                skill_path_str = kwargs.get("skill_path", "")

                if not skill_path_str:
                    return ToolResult(
                        success=False,
                        tool_name=self.meta.name,
                        error="No skill path provided"
                    )

                skill_path = Path(skill_path_str)

                if not skill_path.exists():
                    return ToolResult(
                        success=False,
                        tool_name=self.meta.name,
                        error=f"Skill file not found: {skill_path_str}"
                    )

                # Validate skill
                if self.skill_loader is None:
                    self.skill_loader = SkillLoader(telos=self.telos)

                is_valid, issues = await self.skill_loader.validate_skill(skill_path)

                return ToolResult(
                    success=is_valid,
                    tool_name=self.meta.name,
                    data="Skill is valid" if is_valid else "Skill validation failed",
                    execution_time_ms=(time.time() - start_time) * 1000,
                    metadata={
                        "valid": is_valid,
                        "issues": issues,
                        "skill_path": str(skill_path)
                    }
                )

            else:
                return ToolResult(
                    success=False,
                    tool_name=self.meta.name,
                    error=f"Unknown action: {action}"
                )

        except Exception as e:
            logger.exception("skill.tool.error", action=action, error=str(e))
            return ToolResult(
                success=False,
                tool_name=self.meta.name,
                error=f"Skill operation failed: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )

# tools/builtin/skill_tool.py
"""Tool interface to the SkillLoader.

Agents use this to list, load, and invoke skills at runtime.
"""
from typing import Optional, TYPE_CHECKING

import structlog

from tools.base_tool import BaseTool, ToolMeta, ToolResult

if TYPE_CHECKING:
    from skills.skill_loader import SkillLoader

logger = structlog.get_logger()


class SkillTool(BaseTool):
    def __init__(self, loader: Optional["SkillLoader"] = None) -> None:
        self.loader = loader

    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="skill",
            description="List, load, or invoke agent skills. Install new skills from GitHub URLs.",
            parameters={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list", "load", "invoke", "install"]},
                    "skill_name": {"type": "string"},
                    "github_url": {"type": "string"},
                    "context": {"type": "object"},
                },
                "required": ["action"],
            },
            risk_score=0.2,
            categories=["skills", "meta"],
        )

    async def execute(
        self,
        action: str,
        skill_name: str = "",
        github_url: str = "",
        context: dict = None,
        **kwargs,
    ) -> ToolResult:
        if self.loader is None:
            return ToolResult(success=False, tool_name="skill", error="SkillLoader not attached")

        try:
            if action == "list":
                skills = self.loader.list_skills()
                return ToolResult(
                    success=True,
                    tool_name="skill",
                    data={"skills": [{"name": s.name, "capabilities": s.capabilities} for s in skills]},
                )

            elif action == "load":
                skill = self.loader.load_from_file(skill_name)
                return ToolResult(success=True, tool_name="skill", data={"loaded": skill.name})

            elif action == "invoke":
                chunks = []
                async for chunk in self.loader.invoke_skill(skill_name, context or {}):
                    chunks.append(chunk)
                return ToolResult(success=True, tool_name="skill", data={"output": "".join(chunks)})

            elif action == "install":
                skill = self.loader.load_from_github(github_url)
                return ToolResult(success=True, tool_name="skill", data={"installed": skill.name})

            else:
                return ToolResult(success=False, tool_name="skill", error=f"Unknown action: {action}")

        except Exception as e:
            return ToolResult(success=False, tool_name="skill", error=str(e))

# skills/__loader__.py
"""Skill loader — converts .md skill files into callable agent capabilities.

A skill is:
- A .md file with YAML frontmatter (machine-parseable metadata)
- Natural language body (LLM-interpretable instructions)
- Required tools declared upfront (dependency resolution before invocation)
- Telos alignment score (validated on load — rejects misaligned skills)

Skill files can be:
- Local (scanned from skills/builtin/ on startup)
- Installed from GitHub URL (fetched, validated, persisted)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator, Optional, TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from gateway.llm_gateway import LLMGateway
    from tools.registry import ToolRegistry
    from core.telos_core import TelosCore

logger = structlog.get_logger()

# Minimum telos alignment score to load a skill
DEFAULT_MIN_TELOS = 0.7


@dataclass
class SkillMeta:
    name: str
    version: str
    capabilities: list[str]
    tools_required: list[str]
    telos_alignment: float
    author: str = ""
    body: str = ""  # Full markdown body (LLM instructions)
    source_path: str = ""


class SkillLoader:
    def __init__(
        self,
        skills_dir: Optional[Path] = None,
        min_telos_alignment: float = DEFAULT_MIN_TELOS,
        llm: Optional["LLMGateway"] = None,
        registry: Optional["ToolRegistry"] = None,
        telos: Optional["TelosCore"] = None,
    ) -> None:
        self.skills_dir = Path(skills_dir) if skills_dir else Path(__file__).parent / "builtin"
        self.min_telos = min_telos_alignment
        self.llm = llm
        self.registry = registry
        self.telos = telos
        self._skills: dict[str, SkillMeta] = {}

    def scan(self) -> int:
        """Scan skills_dir and load all valid .md skills."""
        loaded = 0
        if not self.skills_dir.exists():
            logger.warning("skills.scan.dir_not_found", path=str(self.skills_dir))
            return 0

        for md_file in sorted(self.skills_dir.glob("*.md")):
            try:
                skill = self.load_from_file(str(md_file))
                self._skills[skill.name] = skill
                loaded += 1
                logger.info("skills.loaded", name=skill.name)
            except Exception as e:
                logger.warning("skills.load_failed", file=md_file.name, error=str(e))

        return loaded

    def load_from_file(self, path: str) -> SkillMeta:
        """Parse a .md skill file into SkillMeta."""
        content = Path(path).read_text(encoding="utf-8")
        skill = self._parse_skill(content, source_path=path)
        self._validate_telos(skill)
        return skill

    def load_from_github(self, url: str) -> SkillMeta:
        """Fetch a skill .md from GitHub raw URL, validate, and register."""
        import httpx
        raw_url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
        response = httpx.get(raw_url, timeout=20)
        response.raise_for_status()

        skill = self._parse_skill(response.text, source_path=url)
        self._validate_telos(skill)

        # Persist locally
        save_path = Path(__file__).parent / "installed" / f"{skill.name}.md"
        save_path.parent.mkdir(exist_ok=True)
        save_path.write_text(response.text, encoding="utf-8")
        skill.source_path = str(save_path)

        self._skills[skill.name] = skill
        logger.info("skills.github.installed", name=skill.name, url=url)
        return skill

    def list_skills(self) -> list[SkillMeta]:
        return list(self._skills.values())

    def get(self, name: str) -> Optional[SkillMeta]:
        return self._skills.get(name)

    async def invoke_skill(self, skill_name: str, context: dict) -> AsyncIterator[str]:
        """Invoke a skill via LLM interpretation of its body."""
        skill = self._skills.get(skill_name)
        if skill is None:
            raise ValueError(f"Skill '{skill_name}' not found")

        if self.llm is None:
            raise RuntimeError("LLMGateway required for skill invocation")

        # Verify required tools are available
        if self.registry:
            missing = [t for t in skill.tools_required if self.registry.get(t) is None]
            if missing:
                raise RuntimeError(f"Skill '{skill_name}' requires missing tools: {missing}")

        from gateway.llm_gateway import LLMRequest
        system = f"""You are invoking the skill: {skill.name}

Skill instructions:
{skill.body}

Available context: {context}

Execute the skill goal. Use tools as needed. Return results directly."""

        req = LLMRequest(
            messages=[{"role": "user", "content": f"Invoke skill: {skill_name}\nContext: {context}"}],
            system=system,
            max_tokens=2048,
            stream=True,
        )

        async for token in self.llm.stream(req):
            yield token

    def _parse_skill(self, content: str, source_path: str = "") -> SkillMeta:
        """Parse YAML frontmatter + markdown body."""
        # Extract YAML frontmatter between --- delimiters
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not frontmatter_match:
            raise ValueError("Skill file missing YAML frontmatter (--- block)")

        yaml_block = frontmatter_match.group(1)
        body = frontmatter_match.group(2).strip()

        # Parse YAML fields manually (avoid yaml dep, keep it simple)
        fields: dict = {}
        for line in yaml_block.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip()
                val = val.strip()
                # Parse list syntax: [a, b, c]
                if val.startswith("[") and val.endswith("]"):
                    items = [i.strip().strip("'\"") for i in val[1:-1].split(",")]
                    fields[key] = [i for i in items if i]
                else:
                    fields[key] = val.strip("'\"")

        return SkillMeta(
            name=fields.get("name", Path(source_path).stem),
            version=fields.get("version", "1.0.0"),
            capabilities=fields.get("capabilities", []),
            tools_required=fields.get("tools_required", []),
            telos_alignment=float(fields.get("telos_alignment", 0.5)),
            author=fields.get("author", ""),
            body=body,
            source_path=source_path,
        )

    def _validate_telos(self, skill: SkillMeta) -> None:
        if skill.telos_alignment < self.min_telos:
            raise ValueError(
                f"Skill '{skill.name}' telos_alignment={skill.telos_alignment} "
                f"below minimum {self.min_telos}. Rejected."
            )

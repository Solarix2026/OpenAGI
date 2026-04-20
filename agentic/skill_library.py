# Copyright (c) 2026 ApeironAI
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""
skill_library.py — Skill management and discovery

list_skills() → scan ./skills/*.yaml
install_skill(url) → download + yaml.safe_load validate + save
create_skill_from_conversation(history) → NVIDIA extracts reusable YAML
export_skill(name) → return YAML string
"""
import yaml
import json
import logging
import re
from pathlib import Path
from core.llm_gateway import call_nvidia
import urllib.request
import urllib.error

log = logging.getLogger("SkillLibrary")
SKILLS_DIR = Path("./skills")


class SkillLibrary:
    def __init__(self):
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        self._ensure_starter_skills()

    def _ensure_starter_skills(self):
        """Create starter skills if they don't exist."""
        starters = {
            "video_deck": {
                "description": "Generate a video presentation deck",
                "parameters": {
                    "topic": {"type": "string", "required": True},
                    "slides": {"type": "integer", "default": 10},
                    "style": {"type": "string", "default": "professional"}
                },
                "steps": [
                    {"id": "research", "type": "tool", "tool": "websearch", "params": {"query": "{{topic}} latest trends"}},
                    {"id": "outline", "type": "llm", "prompt": "Create a {{slides}}-slide outline for: {{topic}}. Style: {{style}}. Research: {{research.text}}"},
                    {"id": "save", "type": "tool", "tool": "write_file", "params": {"path": "decks/{{topic|replace(' ', '_')}}_deck.md", "content": "{{outline.text}}"}}
                ]
            },
            "saas_scaffold": {
                "description": "Generate SaaS project scaffold",
                "parameters": {
                    "name": {"type": "string", "required": True},
                    "description": {"type": "string", "required": True},
                    "features": {"type": "list", "default": ["auth", "dashboard"]}
                },
                "steps": [
                    {"id": "design", "type": "llm", "prompt": "Design a FastAPI SaaS called '{{name}}'. Features: {{features}}. Description: {{description}}. Return JSON: {main_py: '...', index_html: '...'}"},
                    {"id": "mkdir", "type": "tool", "tool": "shell_command", "params": {"command": "mkdir -p workspace/projects/{{name}}"}},
                    {"id": "write_main", "type": "tool", "tool": "write_file", "params": {"path": "workspace/projects/{{name}}/main.py", "content": "{{design.text}}"}}
                ]
            },
            "morning_brief": {
                "description": "Generate morning briefing",
                "parameters": {},
                "steps": [
                    {"id": "weather", "type": "tool", "tool": "memory_search", "params": {"query": "user location weather"}},
                    {"id": "goals", "type": "tool", "tool": "list_goals", "params": {}},
                    {"id": "news", "type": "tool", "tool": "world_events", "params": {"categories": ["technology", "ai"]}},
                    {"id": "briefing", "type": "llm", "prompt": "Create a warm morning briefing. Weather: {{weather.text}}, Goals: {{goals.text}}, News: {{news.text}}. Be brief and encouraging."}
                ]
            },
            "lead_tracker": {
                "description": "Track and organize pipeline leads",
                "parameters": {
                    "lead_info": {"type": "string", "required": True}
                },
                "steps": [
                    {"id": "parse", "type": "llm", "prompt": "Parse lead info: {{lead_info}}. Return JSON: {company, contact, status, priority}"},
                    {"id": "save", "type": "tool", "tool": "write_file", "params": {"path": "leads/{{parse.company|default('unknown')}}.json", "content": "{{parse.text}}"}}
                ]
            },
            "code_review": {
                "description": "Review code for issues",
                "parameters": {
                    "file_path": {"type": "string", "required": True}
                },
                "steps": [
                    {"id": "read", "type": "tool", "tool": "read_file", "params": {"path": "{{file_path}}"}},
                    {"id": "review", "type": "llm", "prompt": "Review this code and identify: bugs, security issues, performance problems, style violations. Code: {{read.content}}"},
                    {"id": "report", "type": "tool", "tool": "write_file", "params": {"path": "reviews/{{file_path|replace('/','_')}}_review.md", "content": "## Code Review\n{{review.text}}"}}
                ]
            }
        }

        for name, spec in starters.items():
            path = SKILLS_DIR / f"{name}.yaml"
            if not path.exists():
                try:
                    path.write_text(yaml.dump(spec, default_flow_style=False, allow_unicode=True))
                    log.info(f"[SKILL] Created starter: {name}")
                except Exception as e:
                    log.warning(f"Failed to create starter {name}: {e}")

    def list_skills(self) -> list[str]:
        """List all available skill names."""
        return [p.stem for p in SKILLS_DIR.glob("*.yaml")]

    def get_skill(self, name: str) -> dict | None:
        """Get a skill spec by name."""
        path = SKILLS_DIR / f"{name}.yaml"
        if path.exists():
            try:
                return yaml.safe_load(path.read_text())
            except Exception:
                pass
        return None

    def install_skill(self, url: str) -> dict:
        """Download and install a skill from URL."""
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                content = resp.read().decode('utf-8')

            # Validate YAML
            spec = yaml.safe_load(content)
            if not spec or not isinstance(spec, dict):
                return {"success": False, "error": "Invalid YAML format"}

            if "steps" not in spec:
                return {"success": False, "error": "Missing 'steps' in skill definition"}

            # Infer filename from URL or skill name
            name = spec.get("name", url.split("/")[-1].replace(".yaml", ""))
            path = SKILLS_DIR / f"{name}.yaml"
            path.write_text(content)

            log.info(f"[SKILL] Installed: {name}")
            return {"success": True, "name": name, "path": str(path)}

        except urllib.error.URLError as e:
            return {"success": False, "error": f"Download failed: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_skill_from_conversation(self, history: list[dict]) -> dict:
        """Extract a reusable skill from conversation history using LLM."""
        import time
        prompt = f"""Analyze this conversation and extract a reusable AI skill.

Conversation: {json.dumps(history, ensure_ascii=False)}

Create a YAML skill definition with:
- description: what this skill does
- parameters: input parameters
- steps: ordered steps using tools or LLM calls

Return ONLY the YAML, no explanation:"""

        raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=800)
        try:
            spec = yaml.safe_load(raw)
            if not spec:
                return {"success": False, "error": "Failed to parse skill"}

            name = spec.get("name", f"extracted_skill_{int(time.time())}")
            path = SKILLS_DIR / f"{name}.yaml"
            path.write_text(raw)
            return {"success": True, "name": name, "spec": spec}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def export_skill(self, name: str) -> str:
        """Export a skill as YAML string."""
        path = SKILLS_DIR / f"{name}.yaml"
        if path.exists():
            return path.read_text()
        return ""

    def delete_skill(self, name: str) -> bool:
        """Delete a skill."""
        path = SKILLS_DIR / f"{name}.yaml"
        if path.exists():
            path.unlink()
            return True
        return False

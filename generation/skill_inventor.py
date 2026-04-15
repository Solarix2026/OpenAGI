# Copyright (c) 2026 HackerTMJ
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""
skill_inventor.py — Dynamic skill generation (Google AI Edge Gallery style)

Like Google AI Edge Gallery's Agent Skills, but:
- NVIDIA generates the skill JS/HTML dynamically instead of pre-written files
- Skills stored in ./skills/invented_html/
- Called via WebUI iframe injection or direct data passing

Skills are HTML+JS files that:
1. Receive JSON data from the agent (action + params)
2. Render a visual result (chart, map, tracker, dashboard)
3. Return a text summary back to the agent

Usage:
- "invent a skill that shows a calorie tracker"
- "create a skill to visualize my stock portfolio"
- "build a skill for a pomodoro timer"
"""

import logging
import re
import json
from pathlib import Path
from core.llm_gateway import call_nvidia

log = logging.getLogger("SkillInventor")

SKILLS_HTML_DIR = Path("./skills/invented_html")


class SkillInventor:
    def __init__(self):
        SKILLS_HTML_DIR.mkdir(parents=True, exist_ok=True)

    def invent_skill(self, description: str) -> dict:
        """
        Generate a new HTML+JS skill from natural language description.

        Returns: {success, skill_name, path, description, actions, preview}
        """
        # Step 1: Design the skill
        design_prompt = f"""Design an AI agent skill (HTML+JS widget) for: "{description}"

Return JSON:
{{
  "skill_name": "snake_case_name",
  "description": "one line",
  "actions": [
    {{"name": "action_name", "params": {{"key": "type"}}, "description": "what it does"}}
  ],
  "display": "what the visual looks like"
}}"""

        raw = call_nvidia([{"role": "user", "content": design_prompt}],
                          max_tokens=400, fast=True)
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if not m:
            return {"success": False, "error": "Design failed"}

        try:
            design = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid JSON in design"}

        skill_name = design.get("skill_name", "custom_skill")

        # Step 2: Generate the HTML skill
        html_prompt = f"""Generate a complete HTML+JS skill file for an AI assistant.

Skill: {description}
Design: {json.dumps(design)}

The HTML file must:
1. Export a function: window.executeAction(action, data) that handles all actions
2. Render beautiful UI using Tailwind CDN (dark theme #0d1117, text #e2e8f0)
3. Use localStorage for persistence between calls (key: '{skill_name}_data')
4. Return a text summary string from executeAction()
5. Show results visually in the page body
6. Fit in a small widget (max 400px wide)

Structure:
<!DOCTYPE html>
<html>
<head>
<script src="https://cdn.tailwindcss.com"></script>
<style>body{{background:#0d1117;color:#e2e8f0;font-family:sans-serif;padding:16px}}</style>
</head>
<body>
<!-- UI here -->
<script>
// localStorage persistence
window.executeAction = function(action, data) {{
  // implementation
  return "Summary string for the agent";
}};
</script>
</body>
</html>

Write ONLY the HTML, no explanation:"""

        html_code = call_nvidia([{"role": "user", "content": html_prompt}],
                                max_tokens=3000)
        html_code = re.sub(r'```html?\n?|```\n?', '', html_code).strip()

        # Save
        skill_path = SKILLS_HTML_DIR / f"{skill_name}.html"
        skill_path.write_text(html_code, encoding="utf-8")

        # Generate YAML descriptor for recipe_engine compatibility
        yaml_content = f"""description: {design.get('description', description)}
skill_name: {skill_name}
type: html_skill
html_path: {skill_path}
actions:
"""
        for action in design.get("actions", []):
            yaml_content += f"  - name: {action['name']}\n"
            yaml_content += f"    description: {action.get('description', '')}\n"

        yaml_path = Path("./skills") / f"{skill_name}.yaml"
        yaml_path.write_text(yaml_content)

        log.info(f"[SKILL INVENTOR] Created: {skill_name}")

        return {
            "success": True,
            "skill_name": skill_name,
            "path": str(skill_path),
            "description": design.get("description", ""),
            "actions": design.get("actions", []),
            "preview": f"Skill '{skill_name}' created. Use it by saying: 'use {skill_name} to...'"
        }

    def list_invented_skills(self) -> list:
        return [{"name": p.stem, "path": str(p)} for p in SKILLS_HTML_DIR.glob("*.html")]

    def get_skill_html(self, skill_name: str) -> str:
        """Get HTML content of an invented skill."""
        path = SKILLS_HTML_DIR / f"{skill_name}.html"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def register_as_tool(self, registry):
        """Register invent_skill as a tool in the executor registry."""
        inv = self

        def invent_skill_tool(params: dict) -> dict:
            desc = params.get("description", "") or params.get("skill", "")
            if not desc:
                return {"success": False, "error": "Describe the skill you want to create"}
            return inv.invent_skill(desc)

        registry.register(
            "invent_skill",
            invent_skill_tool,
            "Invent a new interactive HTML+JS skill for any use case: trackers, charts, calculators, dashboards",
            {"description": {"type": "string", "required": True, "description": "What the skill should do"}},
            "skill_inventor"
        )

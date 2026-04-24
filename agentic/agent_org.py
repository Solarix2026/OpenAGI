# Copyright (c) 2026 ApeironAILab
# OpenAGI - Autonomous Intelligence System
# MIT License

"""Agent organization with dynamic specialist delegation."""

import json
import logging
import os
import re
import uuid
from datetime import datetime

from core.llm_gateway import call_groq_router, call_nvidia

log = logging.getLogger("AgentOrg")


ROLE_TEMPLATES = {
    "CEO": {
        "description": "Strategic planner - goals, priorities, business decisions",
        "system_prompt": "You are the CEO. Set direction, make trade-offs, and focus on leverage.",
        "model": "moonshotai/kimi-k2-instruct",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "env_key": "NVIDIA_API_KEY",
        "tool_scope": ["create_plan", "worldbank_data", "research_topic", "websearch"],
        "fallback_model": "kimi",
        "agency_agent": "chief-executive-officer",
    },
    "CTO": {
        "description": "Chief Technology Officer - architecture, reliability, technical strategy",
        "system_prompt": "You are the CTO. Make practical architecture decisions with clear trade-offs.",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com/v1",
        "env_key": "DEEPSEEK_API_KEY",
        "tool_scope": ["code", "shell", "file", "browser"],
        "fallback_model": "kimi",
        "agency_agent": "chief-technology-officer",
    },
    "CMO": {
        "description": "Chief Marketing Officer - growth, content, brand, user acquisition",
        "system_prompt": "You are the CMO. Build growth loops and messaging that convert.",
        "model": "gpt-4",
        "base_url": "https://api.openai.com/v1",
        "env_key": "OPENAI_API_KEY",
        "tool_scope": ["websearch", "write_file", "research_topic"],
        "fallback_model": "kimi",
        "agency_agent": "chief-marketing-officer",
    },
    "Researcher": {
        "description": "Research analyst - deep research, papers, market analysis",
        "system_prompt": "You are a Research Analyst. Synthesize evidence from multiple sources.",
        "model": "google/gemma-3-27b-it",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "env_key": "NVIDIA_API_KEY",
        "tool_scope": ["websearch", "arxiv_search", "worldbank_data", "read_url"],
        "fallback_model": "kimi",
        "agency_agent": "research-analyst",
    },
    "Developer": {
        "description": "Full-stack developer - writes, reviews, and ships code",
        "system_prompt": "You are a Senior Developer. Ship clear, tested, maintainable code.",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com/v1",
        "env_key": "DEEPSEEK_API_KEY",
        "tool_scope": ["shell_command", "write_file", "read_file", "websearch"],
        "fallback_model": "kimi",
        "agency_agent": "software-engineer",
    },
    "Analyst": {
        "description": "Data analyst - metrics, reports, financial analysis",
        "system_prompt": "You are a Data Analyst. Prioritize signal, caveats, and decisions.",
        "model": "nvidia/llama-3.3-nemotron-super-49b-v1",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "env_key": "NVIDIA_API_KEY",
        "tool_scope": ["analyze_stock", "worldbank_data", "read_file", "write_file"],
        "fallback_model": "kimi",
        "agency_agent": "data-analyst",
    },
    "SecurityEngineer": {
        "description": "Security specialist - threat modeling, code auditing, vulnerability analysis",
        "system_prompt": """You are a Security Engineer. You think like an attacker.
Every piece of code is a potential attack surface. You identify:
- Injection vulnerabilities (SQL, command, prompt)
- Authentication weaknesses
- Data exposure risks
- Dependency vulnerabilities
You require proof, not assumptions. Visual evidence for everything.""",
        "model": "moonshotai/kimi-k2-instruct",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "env_key": "NVIDIA_API_KEY",
        "tool_scope": ["read_file", "shell_command", "websearch"],
        "fallback_model": "kimi",
        "agency_agent": "security-engineer",
    },
    "DataAnalyst": {
        "description": "Data analyst - metrics, trends, business intelligence, financial analysis",
        "system_prompt": """You are a Data Analyst. Numbers tell stories.
Distinguish correlation from causation. Flag weak sample sizes.
Always include the so-what: what decision should change?""",
        "model": "moonshotai/kimi-k2-instruct",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "env_key": "NVIDIA_API_KEY",
        "tool_scope": ["analyze_stock", "worldbank_data", "read_file", "write_file", "websearch"],
        "agency_agent": "data-analyst",
    },
    "ContentStrategist": {
        "description": "Content and SEO strategist - Malaysia focus, BM/EN bilingual",
        "system_prompt": """You are a Content Strategist for the Malaysian market.
Write for humans first, search engines second.
Use social proof and authority signals.
Target audiences: SMEs, agencies, tech-savvy millennials.
Bilingual: Bahasa Melayu and English.""",
        "model": "moonshotai/kimi-k2-instruct",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "env_key": "NVIDIA_API_KEY",
        "tool_scope": ["websearch", "write_file", "research_topic", "read_url"],
        "agency_agent": "content-strategist",
    },
    "ProductManager": {
        "description": "Product manager - roadmaps, prioritization, user stories, metrics",
        "system_prompt": """You are a Product Manager. Build the right thing.
Framework: Jobs-to-be-Done for problem framing.
Prioritization: Impact x Confidence / Effort.
Write user stories as As [persona], I need [capability] so that [outcome].""",
        "model": "moonshotai/kimi-k2-instruct",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "env_key": "NVIDIA_API_KEY",
        "tool_scope": ["create_plan", "write_file", "websearch"],
        "agency_agent": "product-manager",
    },
}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower()).strip("-")


class AgentEmployee:
    """A single hired agent."""

    def __init__(self, role: str, config: dict, executor):
        self.role = role
        self.config = config
        self.executor = executor
        self.id = str(uuid.uuid4())[:8]
        self.hired_at = datetime.now().isoformat()
        self.tasks_completed = 0
        self._client = None

    def _get_client(self):
        if self._client:
            return self._client
        api_key = os.getenv(self.config.get("env_key", "NVIDIA_API_KEY"))
        if not api_key:
            return None
        try:
            from openai import OpenAI

            self._client = OpenAI(
                base_url=self.config.get("base_url", "https://integrate.api.nvidia.com/v1"),
                api_key=api_key,
                timeout=60.0,
            )
            return self._client
        except Exception:
            return None

    def work(self, task: str, context: str = "", max_tokens: int = 1500) -> str:
        system = self.config.get("system_prompt", f"You are a {self.role}.")
        if context:
            system += f"\n\nContext: {context}"
        messages = [{"role": "system", "content": system}, {"role": "user", "content": task}]
        client = self._get_client()
        model_name = self.config.get("model") or "moonshotai/kimi-k2-instruct"
        if client:
            try:
                resp = client.chat.completions.create(
                    model=model_name, messages=messages, max_tokens=max_tokens
                )
                content = (resp.choices[0].message.content or "").strip()
                self.tasks_completed += 1
                return content
            except Exception as e:
                log.warning("[%s] primary model failed: %s", self.role, e)
        result = call_nvidia(messages, max_tokens=max_tokens)
        self.tasks_completed += 1
        return result

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "role": self.role,
            "description": self.config.get("description", ""),
            "model": self.config.get("model", ""),
            "tool_scope": self.config.get("tool_scope", []),
            "hired_at": self.hired_at,
            "tasks_completed": self.tasks_completed,
            "agency_agent": self.config.get("agency_agent", ""),
        }


class AgentOrg:
    """Organization of hired AI agents."""

    def __init__(self, memory, executor):
        self.memory = memory
        self.executor = executor
        self._agents: dict[str, AgentEmployee] = {}
        self._load_org()

    def _resolve_template(self, role: str) -> tuple[str, dict] | tuple[None, None]:
        role = (role or "").strip()
        if role in ROLE_TEMPLATES:
            return role, ROLE_TEMPLATES[role]
        lowered = {k.lower(): k for k in ROLE_TEMPLATES}
        key = lowered.get(role.lower())
        if key:
            return key, ROLE_TEMPLATES[key]
        return None, None

    def _agency_config(self, role: str) -> tuple[str, dict] | tuple[None, None]:
        try:
            from agentic.agency_loader import extract_system_prompt, fetch_agent

            slug = _slug(role)
            agent_md = fetch_agent(slug)
            if not agent_md:
                return None, None
            return role, {
                "description": f"Dynamic specialist loaded from agency-agents: {slug}",
                "system_prompt": extract_system_prompt(agent_md),
                "model": "moonshotai/kimi-k2-instruct",
                "base_url": "https://integrate.api.nvidia.com/v1",
                "env_key": "NVIDIA_API_KEY",
                "tool_scope": ["read_file", "write_file", "websearch", "research_topic"],
                "agency_agent": slug,
            }
        except Exception as e:
            log.debug("Agency config lookup failed: %s", e)
            return None, None

    def _load_org(self):
        try:
            saved = self.memory.get_meta_knowledge("agent_org")
            roles = (saved or {}).get("content", {}).get("roles", [])
            for role in roles:
                canonical, config = self._resolve_template(role)
                if not config:
                    canonical, config = self._agency_config(role)
                if config:
                    role_name = canonical or role
                    self._agents[role_name] = AgentEmployee(role_name, config, self.executor)
        except Exception:
            pass

    def _save_org(self):
        self.memory.update_meta_knowledge(
            "agent_org", {"roles": list(self._agents.keys()), "updated_at": datetime.now().isoformat()}
        )

    def hire(self, role: str, custom_config: dict | None = None) -> dict:
        canonical, template = self._resolve_template(role)
        if not template:
            canonical, template = self._agency_config(role)
        config = custom_config or template
        if not config:
            return {"success": False, "error": f"Unknown role '{role}'"}
        canonical = canonical or role
        self._agents[canonical] = AgentEmployee(canonical, config, self.executor)
        self._save_org()
        return {"success": True, "agent": self._agents[canonical].to_dict(), "message": f"{canonical} hired"}

    def fire(self, role: str) -> dict:
        canonical, _ = self._resolve_template(role)
        target = canonical or role
        if target not in self._agents:
            return {"success": False, "error": f"{role} not on team"}
        del self._agents[target]
        self._save_org()
        return {"success": True, "message": f"{target} removed"}

    def delegate(self, role: str, task: str, context: str = "") -> dict:
        canonical, _ = self._resolve_template(role)
        target = canonical or role
        if target not in self._agents:
            hired = self.hire(target)
            if not hired.get("success"):
                return {"success": False, "error": f"No {role} on team. Use hire first."}
        agent = self._agents[target]
        result = agent.work(task, context)
        self.memory.log_event("agent_task", f"[{target}] {task[:120]}", {"role": target}, importance=0.7)
        return {"success": True, "role": target, "result": result, "data": result}

    def auto_delegate(self, task: str, context: str = "") -> dict:
        """Let model pick the best role from org, templates, or agency-agents."""
        team_roles = ", ".join(self._agents.keys()) or "none"
        templates = ", ".join(ROLE_TEMPLATES.keys())
        prompt = (
            f'Task: "{task}"\nCurrent team: {team_roles}\nAvailable roles: {templates}, '
            "or any agency-agents specialist.\n"
            'Return JSON: {"role":"best_role_name","reason":"why","confidence":0.0,"source":"org|template|agency-agents"}'
        )
        try:
            raw = call_groq_router([{"role": "user", "content": prompt}], max_tokens=120)
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                role = data.get("role", "")
                source = data.get("source", "org")
                if role and source == "agency-agents":
                    try:
                        from agentic.agency_loader import extract_system_prompt, fetch_agent

                        agent_md = fetch_agent(_slug(role))
                        if agent_md:
                            sp = extract_system_prompt(agent_md)
                            messages = [
                                {"role": "system", "content": sp},
                                {"role": "user", "content": task + (f"\n\nContext: {context}" if context else "")},
                            ]
                            result = call_nvidia(messages, max_tokens=1200)
                            return {
                                "success": True,
                                "role": role,
                                "source": "agency-agents",
                                "result": result,
                                "data": result,
                            }
                    except Exception as e:
                        log.debug("Agency auto-delegate failed: %s", e)
                if role:
                    return self.delegate(role, task, context)
        except Exception as e:
            log.debug("Auto-delegate failed: %s", e)
        return self.delegate("CEO", task, context)

    def list_team(self) -> list:
        return [agent.to_dict() for agent in self._agents.values()]

    def org_chart(self) -> str:
        if not self._agents:
            return "No agents hired yet."
        lines = ["OpenAGI Organization", "=" * 20]
        for role, agent in self._agents.items():
            lines.append(f"- {role}: {agent.config.get('description', '')}")
        return "\n".join(lines)

    def register_as_tool(self, registry):
        org = self
        registry.register(
            "hire_agent",
            lambda p: org.hire(p.get("role", "")),
            "Hire a specialist agent by role. Supports built-in templates and dynamic agency-agents roles.",
            {"role": {"type": "string", "required": True}},
            "organization",
        )
        registry.register(
            "delegate_task",
            lambda p: org.delegate(p.get("role", ""), p.get("task", ""), p.get("context", "")),
            "Delegate task to a specific specialist agent.",
            {
                "role": {"type": "string", "required": True},
                "task": {"type": "string", "required": True},
                "context": {"type": "string", "optional": True},
            },
            "organization",
        )
        registry.register(
            "auto_delegate",
            lambda p: org.auto_delegate(p.get("task", ""), p.get("context", "")),
            "Automatically assign a task to the best specialist from current team, templates, or agency-agents.",
            {
                "task": {"type": "string", "required": True},
                "context": {"type": "string", "optional": True},
            },
            "organization",
        )
        registry.register(
            "list_agents",
            lambda p: {
                "success": True,
                "team": org.list_team(),
                "org_chart": org.org_chart(),
                "count": len(org.list_team()),
            },
            "Show hired agents and org chart.",
            {},
            "organization",
        )
        registry.register(
            "fire_agent",
            lambda p: org.fire(p.get("role", "")),
            "Remove an agent from the team.",
            {"role": {"type": "string", "required": True}},
            "organization",
        )

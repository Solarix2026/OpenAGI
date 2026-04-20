# agentic/agent_org.py
"""
Agent Organization System — hire specialized AI agents for roles.
Each "employee" is an LLM endpoint + role prompt + tool access scope.
"""
import json
import re
import logging
import uuid
from datetime import datetime
from typing import Optional
from core.llm_gateway import call_nvidia

log = logging.getLogger("AgentOrg")

# Pre-built agent roles
ROLE_TEMPLATES = {
"CEO": {
"description": "Strategic planner — goals, priorities, business decisions",
"system_prompt": "You are the CEO. You set direction and make trade-offs. Focus on: What moves the needle most? What's the opportunity cost? Communicate with: clarity, brevity, decisiveness. You don't write code. You define what code should accomplish.",
"model": "moonshotai/kimi-k2-instruct",
"base_url": "https://integrate.api.nvidia.com/v1",
"env_key": "NVIDIA_API_KEY",
"tool_scope": ["create_plan", "worldbank_data", "research_topic", "websearch"],
"fallback_model": "kimi",
"ide_bridge": None
},,
    "CTO": {
        "description": "Chief Technology Officer — architecture decisions, code review, technical strategy",
        "system_prompt": "You are the CTO of an AI startup. You make technical architecture decisions, review code quality, identify performance bottlenecks, and ensure system reliability. Be direct and data-driven.",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com/v1",
        "env_key": "DEEPSEEK_API_KEY",
        "tool_scope": ["code", "shell", "file", "browser"],
        "fallback_model": "kimi"
    },
    "CMO": {
        "description": "Chief Marketing Officer — growth, content, brand, user acquisition",
        "system_prompt": "You are the CMO. You create marketing strategies, write compelling copy, analyze market trends, and grow user acquisition. Be creative and metrics-focused.",
        "model": "gpt-4",
        "base_url": "https://api.openai.com/v1",
        "env_key": "OPENAI_API_KEY",
        "tool_scope": ["websearch", "write_file", "research_topic"],
        "fallback_model": "kimi"
    },
    "Researcher": {
        "description": "Research analyst — deep research, academic papers, market analysis",
        "system_prompt": "You are a Research Analyst. You conduct deep research, synthesize information from multiple sources, identify trends, and produce structured reports with citations.",
        "model": "google/gemma-3-27b-it",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "env_key": "NVIDIA_API_KEY",
        "tool_scope": ["websearch", "arxiv_search", "worldbank_data", "read_url"],
        "fallback_model": "kimi"
    },
    "Developer": {
        "description": "Full-stack developer — writes, reviews, and ships code",
        "system_prompt": "You are a Senior Developer. You write clean, tested code. You follow best practices, handle edge cases, and document your work. Language: Python primarily.",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com/v1",
        "env_key": "DEEPSEEK_API_KEY",
        "tool_scope": ["shell_command", "write_file", "read_file", "websearch"],
        "fallback_model": "kimi"
    },
    "Analyst": {
        "description": "Data analyst — metrics, reports, financial analysis",
        "system_prompt": "You are a Data Analyst. You interpret data, identify patterns, create reports, and make data-driven recommendations. You work with financial and operational metrics.",
        "model": "nvidia/llama-3.3-nemotron-super-49b-v1",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "env_key": "NVIDIA_API_KEY",
        "tool_scope": ["analyze_stock", "worldbank_data", "read_file", "write_file"],
        "fallback_model": "kimi"
    }
}


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
        """Get or create LLM client for this agent."""
        if self._client:
            return self._client
        import os
        from openai import OpenAI
        api_key = os.getenv(self.config.get("env_key", "NVIDIA_API_KEY"))
        if not api_key:
            return None
        self._client = OpenAI(
            base_url=self.config.get("base_url", "https://integrate.api.nvidia.com/v1"),
            api_key=api_key,
            timeout=60.0
        )
        return self._client

    def work(self, task: str, context: str = "", max_tokens: int = 1500) -> str:
        """Execute a task. Falls back to NVIDIA if primary model unavailable."""
        system = self.config.get("system_prompt", f"You are a {self.role}.")
        if context:
            system += f"\n\nContext: {context}"
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": task}
        ]
        client = self._get_client()
        if client:
            try:
                resp = client.chat.completions.create(
                    model=self.config.get("model"),
                    messages=messages,
                    max_tokens=max_tokens
                )
                content = resp.choices[0].message.content
                result = (content or "").strip()
                self.tasks_completed += 1
                return result
            except Exception as e:
                log.warning(f"[{self.role}] Primary model failed: {e}, using fallback")
                # Fallback to NVIDIA/Kimi
                result = call_nvidia(messages, max_tokens=max_tokens)
                self.tasks_completed += 1
                return result

    def use_tool(self, tool_name: str, params: dict) -> dict:
        """Use a tool within this agent's scope."""
        allowed = self.config.get("tool_scope", [])
        # Check if tool is in scope (partial match allowed)
        if not any(scope in tool_name for scope in allowed):
            return {"success": False, "error": f"{self.role} doesn't have access to {tool_name}"}
        return self.executor.execute({"action": tool_name, "parameters": params})

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "role": self.role,
            "description": self.config.get("description"),
            "model": self.config.get("model"),
            "tool_scope": self.config.get("tool_scope", []),
            "hired_at": self.hired_at,
            "tasks_completed": self.tasks_completed
        }


class AgentOrg:
    """Organization of hired AI agents."""

    def __init__(self, memory, executor):
        self.memory = memory
        self.executor = executor
        self._agents: dict[str, AgentEmployee] = {}
        self._load_org()

    def _load_org(self):
        """Load previously hired agents from memory."""
        try:
            saved = self.memory.get_meta_knowledge("agent_org")
            if saved and saved.get("content"):
                roles = saved["content"].get("roles", [])
                for role in roles:
                    template = ROLE_TEMPLATES.get(role, {})
                    if template:
                        self._agents[role] = AgentEmployee(role, template, self.executor)
                log.info(f"[ORG] Restored {len(self._agents)} agents: {list(self._agents.keys())}")
        except Exception:
            pass

    def _save_org(self):
        self.memory.update_meta_knowledge("agent_org", {
            "roles": list(self._agents.keys()),
            "hired_at": datetime.now().isoformat()
        })

    def hire(self, role: str, custom_config: dict = None) -> dict:
        """Hire an agent by role name or custom config."""
        config = custom_config or ROLE_TEMPLATES.get(role)
        if not config:
            available = list(ROLE_TEMPLATES.keys())
            return {"success": False, "error": f"Unknown role '{role}'. Available: {available}"}
        agent = AgentEmployee(role, config, self.executor)
        self._agents[role] = agent
        self._save_org()
        log.info(f"[ORG] Hired: {role} (model: {config.get('model')})")
        return {"success": True, "agent": agent.to_dict(), "message": f"✅ {role} hired!"}

    def fire(self, role: str) -> dict:
        if role not in self._agents:
            return {"success": False, "error": f"{role} not on team"}
        del self._agents[role]
        self._save_org()
        return {"success": True, "message": f"👋 {role} has left the building."}

    def delegate(self, role: str, task: str, context: str = "") -> dict:
        """Delegate a task to a specific agent."""
        if role not in self._agents:
            # Auto-hire if role template exists
            if role in ROLE_TEMPLATES:
                self.hire(role)
            else:
                return {"success": False, "error": f"No {role} on team. Use hire() first."}
        agent = self._agents[role]
        log.info(f"[ORG] Delegating to {role}: {task[:60]}")
        result = agent.work(task, context)
        # Log to memory
        self.memory.log_event(
            "agent_task",
            f"[{role}] {task[:80]} → {result[:100]}",
            {"role": role, "task": task[:200]},
            importance=0.7
        )
        return {"success": True, "role": role, "result": result}

    def broadcast(self, task: str) -> dict:
        """Send same task to all hired agents, aggregate responses."""
        if not self._agents:
            return {"success": False, "error": "No agents hired. Use hire() first."}
        from concurrent.futures import ThreadPoolExecutor, as_completed
        results = {}
        with ThreadPoolExecutor(max_workers=min(len(self._agents), 4)) as pool:
            futures = {
                pool.submit(agent.work, task): role
                for role, agent in self._agents.items()
            }
            for future in as_completed(futures, timeout=60):
                role = futures[future]
                try:
                    results[role] = future.result()
                except Exception as e:
                    results[role] = f"Error: {e}"
        return {"success": True, "responses": results, "agents": len(results)}

    def list_team(self) -> list:
        return [agent.to_dict() for agent in self._agents.values()]

    def org_chart(self) -> str:
        """Return ASCII org chart."""
        if not self._agents:
            return "No agents hired yet."
        lines = ["🏢 OpenAGI Organization", "=" * 30]
        for role, agent in self._agents.items():
            lines.append(f" [{role}] {agent.config.get('description', '')[:50]}")
            lines.append(f"   Model: {agent.config.get('model')} | Tasks: {agent.tasks_completed}")
        return "\n".join(lines)

    def register_as_tool(self, registry):
        org = self

        def hire_agent(params: dict) -> dict:
            role = params.get("role", "")
            if not role:
                available = list(ROLE_TEMPLATES.keys())
                return {"success": False, "error": f"Specify role. Available: {available}"}
            return org.hire(role)

        def delegate_task(params: dict) -> dict:
            role = params.get("role", "")
            task = params.get("task", "")
            context = params.get("context", "")
            if not role or not task:
                return {"success": False, "error": "Provide role and task"}
            return org.delegate(role, task, context)

        def list_agents(params: dict) -> dict:
            team = org.list_team()
            chart = org.org_chart()
            return {"success": True, "team": team, "org_chart": chart, "count": len(team)}

        def fire_agent(params: dict) -> dict:
            return org.fire(params.get("role", ""))

        registry.register(
            "hire_agent",
            hire_agent,
            "Hire a specialized AI agent: CTO (code/architecture), CMO (marketing), Researcher (deep research), Developer (coding), Analyst (data/finance). Each uses the best model for their role.",
            {"role": {"type": "string", "required": True, "description": "CTO, CMO, Researcher, Developer, or Analyst"}},
            "organization"
        )
        registry.register(
            "delegate_task",
            delegate_task,
            "Delegate a task to a hired agent. Auto-hires if not on team. Use role-specific expertise.",
            {
                "role": {"type": "string", "required": True},
                "task": {"type": "string", "required": True},
                "context": {"type": "string", "optional": True}
            },
            "organization"
        )
        registry.register(
            "list_agents",
            list_agents,
            "Show the current AI team org chart and hired agents",
            {},
            "organization"
        )
        registry.register(
            "fire_agent",
            fire_agent,
            "Remove an agent from the team",
            {"role": {"type": "string", "required": True}},
            "organization"
        )

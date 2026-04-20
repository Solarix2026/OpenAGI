# Copyright (c) 2026 ApeironAI
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""
multi_agent_router.py — Route specialized tasks to external LLMs

Models: GPT-4 (OpenAI), Gemini Pro (Google), DeepSeek (deepseek.com),
        Qwen (DashScope), Doubao (ByteDance)

All via their OpenAI-compatible APIs using env keys.
route(task, specialist) → call appropriate model.

Specialists:
- "code" → DeepSeek
- "reasoning" → Gemini
- "creative" → GPT-4

register_as_tool: "specialist_agent" tool.
"""
import os
import logging
from core.llm_gateway import call_nvidia

log = logging.getLogger("MultiAgent")


class MultiAgentRouter:
    def __init__(self, memory):
        self.memory = memory
        self._clients = {}
        self._specialists = {
            "code": {"model": "deepseek-chat", "base_url": "https://api.deepseek.com/v1", "env_key": "DEEPSEEK_API_KEY"},
            "reasoning": {"model": "gemini-1.5-pro", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai", "env_key": "GEMINI_API_KEY"},
            "creative": {"model": "gpt-4", "base_url": "https://api.openai.com/v1", "env_key": "OPENAI_API_KEY"},
            "default": {"model": "nvidia/llama-3.3-nemotron-super-49b-v1", "base_url": "https://integrate.api.nvidia.com/v1", "env_key": "NVIDIA_API_KEY"}
        }

    def _get_client(self, specialist: str):
        """Get or create API client for a specialist."""
        if specialist in self._clients:
            return self._clients[specialist]

        config = self._specialists.get(specialist, self._specialists["default"])
        try:
            from openai import OpenAI
            api_key = os.getenv(config["env_key"])
            if not api_key:
                return None
            client = OpenAI(base_url=config["base_url"], api_key=api_key)
            self._clients[specialist] = (client, config["model"])
            return self._clients[specialist]
        except Exception as e:
            log.warning(f"Failed to init {specialist} client: {e}")
            return None

    def route(self, task: str, specialist: str = "default", messages: list = None, max_tokens=500) -> str:
        """Route task to appropriate specialist LLM."""
        client_info = self._get_client(specialist)
        if not client_info and specialist != "default":
            # Fallback to default
            client_info = self._get_client("default")

        if not client_info:
            # Fall back to NVIDIA
            return call_nvidia(messages or [{"role": "user", "content": task}], max_tokens=max_tokens)

        client, model = client_info
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages or [{"role": "user", "content": task}],
                max_tokens=max_tokens
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            log.error(f"{specialist} call failed: {e}")
            # Fallback to NVIDIA
            return call_nvidia(messages or [{"role": "user", "content": task}], max_tokens=max_tokens)

    def register_as_tool(self, registry):
        router = self

        def specialist_agent(params: dict) -> dict:
            task = params.get("task", "")
            specialist = params.get("specialist", "default")
            if not task:
                return {"success": False, "error": "No task provided"}
            result = router.route(task, specialist)
            return {"success": True, "result": result, "specialist": specialist}

        registry.register(
            "specialist_agent",
            specialist_agent,
            "Route task to a specialist LLM: code (DeepSeek), reasoning (Gemini), creative (GPT-4), or default (NVIDIA)",
            {"task": {"type": "string", "required": True}, "specialist": {"type": "string", "default": "default"}},
            "multi_agent"
        )

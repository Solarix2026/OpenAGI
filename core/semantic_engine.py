# Copyright (c) 2026 HackerTMJ
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/HackerTMJ/OpenAGI

"""
semantic_engine.py — Deep semantic understanding + intent classification

This is the intelligence layer between raw user input and tool execution.
It does NOT do simple keyword matching. It understands:
  - What the user MEANS (semantic intent)
  - What the user HASN'T said (hidden assumptions)
  - What depth of response is appropriate
  - Whether clarification is needed before acting

Architecture:
  Groq → fast JSON intent classification (action type + parameters)
  NVIDIA → semantic depth analysis, clarification decisions, response generation
"""
import re, json, logging
from core.llm_gateway import call_groq_router, call_nvidia

log = logging.getLogger("SemanticEngine")


# ── ROUTING PROMPT ────────────────────────────────────────────────

ROUTING_PROMPT_TEMPLATE = """You are a routing classifier. Return JSON only.

Available tools:
{tool_descriptions}

User input: "{user_input}"

Classify the intent. Return:
{{"intent": "action" or "conversation", "action": "<tool_name>" (if action), "parameters": {{"key": "value"}} (if action), "confidence": 0.0-1.0}}

ROUTING RULES (highest priority first):
1. "search for X", "find X", "look up X", "news about X", "web search X", "tell me about X" → websearch, query=X
2. "open URL/website.com", "go to https://", "navigate to" → browser_navigate
3. "open app/calculator/notepad/chrome" → system_open_app
4. "write/save/create file" → write_file
5. "read/show file" → read_file
6. "run/execute command" → shell_command
7. "what's happening", "world news", "global events" → world_events
8. "recall/remember/what did I say" → memory_search
9. Everything else → conversation

EXAMPLES:
"go to web search openai news" → {{"intent":"action","action":"websearch","parameters":{{"query":"openai latest news"}},"confidence":0.95}}
"open calculator" → {{"intent":"action","action":"system_open_app","parameters":{{"app_name":"calc.exe"}},"confidence":0.99}}
"打开浏览器搜索AI新闻" → {{"intent":"action","action":"websearch","parameters":{{"query":"AI最新新闻"}},"confidence":0.95}}
"what's happening in the world" → {{"intent":"action","action":"world_events","parameters":{{}},"confidence":0.9}}
"how are you" → {{"intent":"conversation","confidence":0.99}}
"morning briefing" → {{"intent":"action","action":"morning_briefing","parameters":{{}},"confidence":0.99}}
"给我早上简报" → {{"intent":"action","action":"morning_briefing","parameters":{{}},"confidence":0.99}}
"what can you do" → {{"intent":"action","action":"system_status","parameters":{{}},"confidence":0.95}}
"evolve yourself" → {{"intent":"action","action":"run_evolution","parameters":{{}},"confidence":0.9}}
"innovate on X" → {{"intent":"action","action":"run_innovation","parameters":{{"problem":"X"}},"confidence":0.9}}
"my goals" → {{"intent":"action","action":"list_goals","parameters":{{}},"confidence":0.95}}
"""



# ── DEPTH ANALYSIS PROMPT ─────────────────────────────────────────

DEPTH_ANALYSIS_PROMPT = """Analyze this user input at semantic depth.

Input: "{user_input}"

Determine:
1. Is this a surface request or does it hide a deeper need?
2. Does executing this immediately produce high-quality output, or does it need clarification first?
3. What is the user's real goal (not just what they said)?

Return JSON:
{{"depth": "execute" | "clarify" | "probe", "real_goal": "what user actually wants", "hidden_assumption": "assumption they're making, or null", "missing_params": ["param1", "param2"], "counter_question": "one precise question to ask, or null", "clarify_reason": "why you need more info, or null"}}

DEPTH GUIDE:
- execute: clear action, no ambiguity. "open calc" = execute.
- clarify: needs 1-2 parameters for quality output.
    "write a script" = clarify (what does it do?)
    "I want abs" = clarify (age/weight/training frequency?)
    "analyze my competition" = clarify (which industry/dimensions?)
- probe: contains a hidden assumption worth surfacing.
    "how do I grow faster" = probe (faster than what? grow in which dimension?)
    "is AI going to replace me" = probe (replace which part of your work?)

For clarify/probe: counter_question must be ONE sharp question in user's language.
Not a list. Not "here are some things to consider". One question.
"""


class SemanticEngine:
    def __init__(self, tool_registry):
        self.registry = tool_registry

    def classify_intent(self, user_input: str) -> dict:
        """
        Fast routing: Groq 8B → JSON intent.
        Returns: {intent, action, parameters, confidence}
        """
        tool_desc = self.registry.get_tool_descriptions()
        prompt = ROUTING_PROMPT_TEMPLATE.format(
            tool_descriptions=tool_desc,
            user_input=user_input.replace('"', "'")
        )

        try:
            raw = call_groq_router(
                [{"role": "user", "content": prompt}],
                max_tokens=250
            )
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                data = json.loads(m.group(0))
                # Validate: action must exist in registry
                if data.get("intent") == "action":
                    if data.get("action") not in self.registry.list_tools():
                        log.warning(f"Unknown tool '{data.get('action')}', routing to conversation")
                        return {"intent": "conversation"}
                return data
        except Exception as e:
            log.error(f"Classification failed: {e}")

        return {"intent": "conversation"}

    def analyze_depth(self, user_input: str) -> dict:
        """
        NVIDIA semantic depth analysis.
        Decides: execute immediately / ask clarifying question / probe assumption.
        """
        prompt = DEPTH_ANALYSIS_PROMPT.format(
            user_input=user_input.replace('"', "'")
        )

        try:
            raw = call_nvidia(
                [{"role": "user", "content": prompt}],
                max_tokens=300,
                fast=True
            )
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                return json.loads(m.group(0))
        except Exception as e:
            log.debug(f"Depth analysis failed: {e}")

        return {"depth": "execute"}

    def should_clarify(self, user_input: str) -> tuple[bool, str | None]:
        """
        Returns (needs_clarification, question_to_ask).
        Only called for non-trivial inputs.
        """
        if len(user_input.split()) <= 4:  # Very short inputs → just execute
            return False, None

        depth = self.analyze_depth(user_input)
        if depth.get("depth") in ("clarify", "probe"):
            return True, depth.get("counter_question")
        return False, None

    def build_response_context(self, user_input: str, tool_result: dict = None, memory_context: str = "", user_ctx: str = "") -> str:
        """Build the full context string for NVIDIA response generation."""
        parts = []

        if user_ctx:
            parts.append(user_ctx)

        if memory_context:
            parts.append(f"Relevant memory:\n{memory_context}")

        if tool_result:
            if tool_result.get("action") == "websearch":
                data = tool_result.get("clean_summary", "")
            else:
                data = str(
                    tool_result.get("data") or
                    tool_result.get("content") or
                    tool_result.get("stdout") or
                    tool_result.get("message") or
                    tool_result.get("error", "")
                )[:600]
            status = "✅ SUCCESS" if tool_result.get("success") else "❌ FAILED"
            parts.append(f"Tool result [{status}]:\n{data}")

        parts.append(f"User said: {user_input}")
        return "\n\n".join(parts)

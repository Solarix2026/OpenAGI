# Copyright (c) 2026 Solarix2026
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

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

ROUTING_PROMPT_TEMPLATE = """PRIORITY BUILD RULES:
- "build * app", "create * app", "make * app", "build me a *" → build_app
- "build a full-stack", "build a SaaS", "scaffold * project" → build_app
- "/mode code" followed by any build request → build_app immediately
- Once in CODE mode, NEVER return conversation for build requests

You are a routing classifier. Return JSON only.

Available tools:
%(tool_descriptions)s

User input: "%(user_input)s"

Classify the intent. Return:
{"intent": "action" or "conversation", "action": "<tool_name>" (if action), "parameters": {"key": "value"} (if action), "confidence": 0.0-1.0}

ROUTING RULES (highest priority first):
1. "search for X", "find X", "look up X", "news about X", "web search X", "tell me about X" → websearch, query=X
2. "open URL/website.com", "go to https://", "navigate to" → browser_navigate
3. "open app/calculator/notepad/chrome" → system_open_app
4. "write/save/create file" → write_file
5. "read/show file" → read_file
6. "run/execute command" → shell_command
7. "what's happening", "world news", "global events" → world_events
8. "recall/remember/what did I say" → memory_search
9. "create/write/save * on desktop" → write_file, path="~/Desktop/{{filename}}"
10. "analyze stock X", "stock price X", "how is X doing" → stock_quote, ticker=X
11. "search arxiv for X", "find papers about X", "academic research X" → arxiv_search, query=X
12. "world bank data X", "GDP of X", "economic data X" → worldbank_data, country=X
13. "read this link/URL/website", "summarize this page", "extract from URL" → read_url, url=X
14. "hire CTO/CMO/Developer/Researcher/Analyst" → hire_agent, role=X
15. "ask/tell/delegate to CTO/researcher/developer", "assign task to X" → delegate_task, role=X, task=Y
16. Everything else → conversation

EXAMPLES:
"create a note on my desktop" → {{"intent":"action","action":"write_file","parameters":{"path":"~/Desktop/note.txt","content":""},"confidence":0.97}
"what's the stock price of AAPL" → {{"intent":"action","action":"stock_quote","parameters":{"ticker":"AAPL"},"confidence":0.98}
"search arxiv for quantum computing" → {{"intent":"action","action":"arxiv_search","parameters":{"query":"quantum computing"},"confidence":0.97}
"get Malaysia GDP data" → {{"intent":"action","action":"worldbank_data","parameters":{"country":"MY","indicator":"gdp_growth"},"confidence":0.95}
"go to web search openai news" → {{{"intent":"action","action":"websearch","parameters":{{"query":"openai latest news"}},"confidence":0.95}}
"open calculator" → {{{"intent":"action","action":"system_open_app","parameters":{{"app_name":"calc.exe"}},"confidence":0.99}}
"打开浏览器搜索AI新闻" → {{{"intent":"action","action":"websearch","parameters":{{"query":"AI最新新闻"}},"confidence":0.95}}
"what's happening in the world" → {{{"intent":"action","action":"world_events","parameters":{{}},"confidence":0.9}}
"how are you" → {{"intent":"conversation","confidence":0.99}}
"morning briefing" → {{{"intent":"action","action":"morning_brief","parameters":{{}},"confidence":0.99}}
"给我早上简报" → {{{"intent":"action","action":"morning_brief","parameters":{{}},"confidence":0.99}}
"what can you do" → {{{"intent":"action","action":"system_status","parameters":{{}},"confidence":0.95}}
"evolve yourself" → {{{"intent":"action","action":"run_evolution","parameters":{{}},"confidence":0.9}}
"innovate on X" → {{{"intent":"action","action":"run_innovation","parameters":{{"problem":"X"}},"confidence":0.9}}
"my goals" → {{{"intent":"action","action":"list_goals","parameters":{{}},"confidence":0.95}}
"read this web URL" → {{{"intent":"action","action":"read_url","parameters":{{"url":"URL"}},"confidence":0.95}}
"hire a CTO" → {{{"intent":"action","action":"hire_agent","parameters":{{"role":"CTO"}},"confidence":0.95}}
"ask the developer to write tests" → {{{"intent":"action","action":"delegate_task","parameters":{{"role":"Developer","task":"write tests"}},"confidence":0.93}}
"""



# ── DEPTH ANALYSIS PROMPT ─────────────────────────────────────────

DEPTH_ANALYSIS_PROMPT = """Analyze user input depth. Return JSON only.
Input: "%(user_input)s"
Return: {"depth": "execute|clarify|probe", "real_goal": "actual intent", "counter_question": "one sharp question or null"}
Rules:
- execute: clear action, 4 words or more
- clarify: missing 1 critical parameter (e.g. "write a script" — what does it do?)
- probe: hides deeper assumption worth surfacing
- counter_question: ONE question in user's language, never null if clarify/probe"""


class SemanticEngine:
    def __init__(self, tool_registry):
        self.registry = tool_registry

    def classify_intent(self, user_input: str) -> dict:
        """
        Fast routing: Groq 8B → JSON intent.
        Returns: {intent, action, parameters, confidence}
        """
        tool_desc = self.registry.get_tool_descriptions()
        prompt = ROUTING_PROMPT_TEMPLATE % {
            "tool_descriptions": tool_desc,
            "user_input": user_input.replace('"', "'")
        }

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
        prompt = DEPTH_ANALYSIS_PROMPT % {
            "user_input": user_input.replace('"', "'")
        }

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

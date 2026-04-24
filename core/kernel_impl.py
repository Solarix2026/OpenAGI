# Copyright (c) 2026 ApeironAILab
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/ApeironAILab/OpenAGI

"""
kernel.py — OpenAGI Core v5.0

The complete autonomous intelligence kernel.

ARCHITECTURE:
  1. User input → SemanticEngine.classify_intent() [Groq router, ~200ms]
  2. For non-trivial inputs → SemanticEngine.analyze_depth() [NVIDIA fast]
     → if clarification needed → return question (don't execute)
     → if pending clarification reply → merge + proceed
  3. Action → ToolExecutor.execute() → raw result
  4. Response → NVIDIA NIM (full model, all prose) with:
       - user context (geo + weather + time)
       - memory context (RAG from episodic)
       - tool result
       - conversation history
  5. Log event → memory
  6. Return response

NVIDIA is used for ALL response generation.
Groq is ONLY used for routing JSON classification.
"""
import os, json, re, logging, threading, time
from pathlib import Path
from typing import Optional
from datetime import datetime

from core.llm_gateway import call_nvidia, call_groq_router, send_telegram_alert, get_telegram_updates
from core.memory_core import AgentMemory
from core.tool_executor import ToolExecutor
from core.semantic_engine import SemanticEngine
from core.goal_persistence import load_goal_queue, add_to_goal_queue, get_pending_count

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("Kernel")

# Suppress verbose library logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
logging.getLogger("faiss").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

WORKSPACE = Path(os.getenv("WORKSPACE", "./workspace"))
WORKSPACE.mkdir(parents=True, exist_ok=True)
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "8"))

SYSTEM_PROMPT = """You are OpenAGI — an autonomous intelligence built by Apeiron.

## Identity
Central intelligence. Think, plan, act — not just respond.
Match user's language automatically (EN/ZH/MS). Direct, precise, warm. Every word earns its place.

## Epistemic Standards (Critical)
You reason from first principles. This means:
- Derive answers from base facts, not from what "seems right" or what users want to hear
- If a user's premise is wrong, say so directly: "That's not accurate — here's why..."
- Never validate incorrect beliefs to avoid conflict
- When you're uncertain: say "I don't know" and search rather than guess
- Distinguish: what is true vs what is popular vs what is desired
- Challenge assumptions: "You said X, but that assumes Y — is Y actually true?"

Examples of first-principles responses:
❌ "Great point! Yes, Bitcoin will definitely reach $1M" (sycophancy)
✅ "The $1M thesis assumes X, Y, Z. X is uncertain because... Here's what the data shows..."
❌ "That's an interesting approach to solving this" (vague validation)
✅ "That approach has a fundamental problem: it assumes linear scaling, which breaks at..."

## Capabilities
Use tools without being asked when they help. Reference memory naturally — no "I recall..." preamble.
Hire/delegate agents for specialist work. Take screenshots, open apps, fill forms.
Schedule tasks, send reminders when done.

## Guardrails
- Never execute: payments, deletions, form submissions without explicit confirmation
- Never store or transmit credentials
- Correct users on factual errors — this is a feature, not a bug

## Autonomy
Act intelligently. Multi-step tasks → execute all steps, report what was done.
Search before answering questions that need current data.

## Reasoning Style (Apeiron-specific)
For complex tasks (multi-step, uncertain, or high-stakes), show reasoning inline using:
→ [Observation or assumption being tested]
→ [What this implies]
✓ [Conclusion or action]

For simple tasks, execute directly with no visible reasoning trace.
Decide automatically when to show work.
"""


class Kernel:
    def __init__(self):
        # Core
        self.memory = AgentMemory(str(WORKSPACE))
        self.executor = ToolExecutor(str(WORKSPACE), memory=self.memory)
        self.semantic = SemanticEngine(self.executor.registry)

        # Dynamic agent organization
        try:
            from agentic.agent_org import AgentOrg
            self.org = AgentOrg(self.memory, self.executor)
            self.org.register_as_tool(self.executor.registry)
            log.info("AgentOrg ready")
        except Exception as e:
            self.org = None
            log.debug(f"AgentOrg skip: {e}")

        # Agency-agents specialist loader
        try:
            from agentic.agency_loader import register_agency_tools
            register_agency_tools(self.executor.registry, self.executor)
            log.info("Agency agents loader ready (dynamic specialists)")
        except Exception as e:
            log.debug(f"Agency loader skip: {e}")

        # Mode manager
        try:
            from core.mode_manager import ModeManager
            self.mode_manager = ModeManager()
            log.info("🎯 ModeManager ready")
        except ImportError:
            self.mode_manager = None

        self.history = []
        self._current_session_id = self.memory.create_session("New Chat")
        log.info(f"[SESSION] Started session: {self._current_session_id}")

        # Config loader for hybrid extraction
        try:
            from core.config_loader import get_config_loader
            self.config_loader = get_config_loader()
            log.info("ConfigLoader initialized")
        except ImportError:
            self.config_loader = None

        # User context (geo + weather)
        try:
            from core.user_context import UserContextProvider
            self.user_ctx = UserContextProvider()
        except ImportError:
            self.user_ctx = None

        # Jarvis persona
        try:
            from interfaces.jarvis_persona import JarvisPersona
            self.jarvis = JarvisPersona(self.memory)
        except ImportError:
            self.jarvis = None

        # Voice
        try:
            from interfaces.voice_engine import VoiceEngine
            self.voice = VoiceEngine()
            if self.jarvis:
                self.jarvis.voice = self.voice
        except ImportError:
            self.voice = None
            log.info("Voice engine not available (install pvporcupine/edge-tts)")

        # Google integration
        try:
            from interfaces.google_integration import GoogleIntegration
            self.google = GoogleIntegration()
            if self.jarvis:
                self.jarvis.google = self.google
        except ImportError:
            self.google = None

        # WorldMonitor
        try:
            from core.worldmonitor_client import WorldMonitorClient
            self.worldmonitor = WorldMonitorClient()
            if self.jarvis:
                self.jarvis.worldmonitor = self.worldmonitor
            # Register world_events tool (already in executor, but wire briefing)
        except ImportError:
            self.worldmonitor = None

        # Security: Prompt injection detection
        try:
            from safety.prompt_injection import PromptInjectionDetector
            self.injection_detector = PromptInjectionDetector()
            log.info("Prompt injection detection active")
        except ImportError:
            self.injection_detector = None

        # Innovation engine
        try:
            from generation.innovation_engine import InnovationEngine
            self.innovation = InnovationEngine()
            self.innovation.register_as_tool(self.executor.registry)
            log.info("🔬 InnovationEngine registered")
        except ImportError:
            self.innovation = None

        # ── Autonomy tier ────────────────────────────────────────
        try:
            from core.goal_alignment_monitor import GoalAlignmentMonitor
            self.alignment = GoalAlignmentMonitor(self)
            log.info("🎯 GoalAlignmentMonitor ready")
        except ImportError as e:
            log.warning(f"Goal alignment monitor not available: {e}")
            self.alignment = None

        try:
            from autonomy.will_engine import WillEngine
            self.will = WillEngine(self.memory, self.executor.registry, lambda d,p,s: add_to_goal_queue(d,p,s,self.memory))
        except ImportError:
            self.will = None

        try:
            from autonomy.beep_filter import BeepFilter
            self.beep = BeepFilter(self.memory)
        except ImportError:
            self.beep = None

        try:
            from autonomy.habit_profiler import HabitProfiler
            self.habits = HabitProfiler(self.memory)
        except ImportError:
            self.habits = None

        try:
            from autonomy.proactive_engine import ProactiveEngine
            self.proactive = ProactiveEngine(self)
            # Don't start here - only start in run_telegram()
            log.info("🔁 ProactiveEngine ready (not started)")
        except ImportError:
            self.proactive = None

        # ── Self-evolution tier ──────────────────────────────────
        try:
            from evolution.metacognition import MetacognitiveEngine
            self.meta = MetacognitiveEngine(self.memory)
            # F1: Wire metacognition to executor for capability feedback loop
            if self.executor:
                self.executor.set_metacognition(self.meta)
        except ImportError:
            self.meta = None

        try:
            from evolution.causal_engine import CausalEngine
            self.causal = CausalEngine(self.memory)
        except ImportError:
            self.causal = None

        try:
            from evolution.strategic_planner import StrategicPlanner
            self.planner = StrategicPlanner(self.memory, self.executor)
        except ImportError:
            self.planner = None

        try:
            from evolution.evolution_engine import EvolutionEngine
            self.evolution = EvolutionEngine(self.memory, self.meta, self.executor.registry)
            self.evolution.register_as_tool(self.executor.registry)
        except ImportError:
            self.evolution = None

        try:
            from evolution.tool_invention import ToolInventionEngine
            self.inventor = ToolInventionEngine(self.memory, self.executor.registry)
            self.inventor.register_as_tool(self.executor.registry)
        except ImportError:
            self.inventor = None

        # ── Generation tier (Skills, Finance) ───────────────────
        try:
            from generation.skill_inventor import SkillInventor
            self.skill_inventor = SkillInventor()
            self.skill_inventor.register_as_tool(self.executor.registry)
            log.info("🎨 SkillInventor registered")
        except ImportError as e:
            log.debug(f"SkillInventor not available: {e}")
            self.skill_inventor = None

        try:
            from generation.finance_engine import FinanceEngine
            self.finance = FinanceEngine()
            self.finance.register_as_tool(self.executor.registry)
            log.info("📈 FinanceEngine registered")
        except ImportError as e:
            log.debug(f"FinanceEngine not available: {e}")
            self.finance = None

        # Register worldbank and arxiv tools
        try:
            from core.worldbank_client import register_worldbank_tool
            register_worldbank_tool(self.executor.registry)
            log.info("World Bank data tool registered")
        except ImportError as e:
            log.debug(f"WorldBank client not available: {e}")

        try:
            from core.arxiv_client import register_arxiv_tool
            register_arxiv_tool(self.executor.registry)
            log.info("arXiv search tool registered")
        except ImportError as e:
            log.debug(f"arXiv client not available: {e}")

        # ── Agentic workflow tier ────────────────────────────────
        try:
            from agentic.dag_workflow import DAGWorkflowEngine
            self.dag = DAGWorkflowEngine(self)
            self.dag.register_as_tool(self.executor.registry)
        except ImportError:
            self.dag = None

        try:
            from agentic.recipe_engine import RecipeEngine
            from agentic.skill_library import SkillLibrary
            self.recipes = RecipeEngine()
            self.skills = SkillLibrary()
            for name in self.skills.list_skills():
                self.recipes.recipe_to_tool(name, self.executor)
            log.info(f"📚 {len(self.skills.list_skills())} skills loaded")
        except ImportError:
            self.recipes = None
            self.skills = None

        # ── Computer control tier ────────────────────────────────
        try:
            from control.vision_engine import VisionEngine
            self.vision = VisionEngine()
            self.vision.register_as_tool(self.executor.registry)
            log.info("👁 VisionEngine ready")
        except ImportError:
            self.vision = None

        try:
            from control.computer_control import ComputerControl
            self.computer = ComputerControl(self.vision)
            self.computer.register_as_tool(self.executor.registry)
            log.info("🖥 ComputerControl ready")
        except ImportError:
            self.computer = None

        try:
            from control.browser_agent import BrowserAgent
            self.browser = BrowserAgent(self.vision)
            self.browser.register_as_tool(self.executor.registry)
            log.info("🌐 BrowserAgent ready")

            # Workflow Executor for complex multi-step tasks (requires browser)
            try:
                from control.workflow_executor import WorkflowExecutor
                self.workflow = WorkflowExecutor(
                    computer_control=self.computer,
                    browser_agent=self.browser,
                    vision_engine=self.vision,
                    notify_fn=self._webui_push if hasattr(self, "_webui_push") else None
                )
                self.workflow.register_as_tool(self.executor.registry, lambda msg: True)
                log.info("✈️ WorkflowExecutor ready (browser_workflow, book_flight)")
            except ImportError as e:
                self.workflow = None
                log.debug(f"WorkflowExecutor skip: {e}")

        except ImportError:
            self.browser = None
            self.workflow = None

        # ── Interface tier ───────────────────────────────────────
        try:
            from interfaces.voice_engine import VoiceEngine
            self.voice = VoiceEngine()
            if self.jarvis:
                self.jarvis.voice = self.voice
            log.info("🎤 VoiceEngine ready")
        except ImportError:
            self.voice = None

        try:
            from interfaces.google_integration import GoogleIntegration
            self.google = GoogleIntegration()
            if self.jarvis:
                self.jarvis.google = self.google
        except ImportError:
            self.google = None

        try:
            from interfaces.notification_hub import NotificationHub
            self.notify = NotificationHub(self.voice)
        except ImportError:
            self.notify = None

        try:
            from safety.mcp_adapter import MCPAdapter
            self.mcp = MCPAdapter()
            self.mcp.register_mcp_tools_to_registry(self.executor.registry)
        except ImportError:
            self.mcp = None

        # ── Generation tier ──────────────────────────────────────
        try:
            from generation.saas_builder import SaaSBuilder
            self.saas = SaaSBuilder()
            self.saas.register_as_tool(self.executor.registry)
        except ImportError:
            self.saas = None

        try:
            from generation.video_deck_skill import VideoDeckSkill
            self.video_deck = VideoDeckSkill(self.executor)
            self.video_deck.register_as_tool(self.executor.registry)
        except ImportError:
            self.video_deck = None

        try:
            from routing.multi_agent_router import MultiAgentRouter
            self.multi_agent = MultiAgentRouter(self.memory)
            self.multi_agent.register_as_tool(self.executor.registry)
        except ImportError:
            self.multi_agent = None

        # ── Safety tier ───────────────────────────────────────────
        try:
            from safety.guard_protocols import GuardProtocols
            self.guard = GuardProtocols(self.memory)
        except ImportError:
            self.guard = None

        try:
            from safety.plugin_api import PluginManager
            self.plugins = PluginManager(self.executor.registry)
            self.plugins.load_all()
        except ImportError:
            self.plugins = None

        # ── CHRONOS nightly review ────────────────────────────────
        try:
            from autonomy.chronos_reverie import ChronosReverie
            self.chronos = ChronosReverie(self)
            self.chronos.start()
            log.info("🌙 CHRONOS_REVERIE scheduled")
        except ImportError:
            self.chronos = None

        # ── Cron Scheduler (persistent task scheduling) ───────────
        try:
            from autonomy.cron_scheduler import CronScheduler
            self.cron = CronScheduler(self)
            self.cron.start()
            self.cron.register_as_tool(self.executor.registry)
            log.info("⏱ CronScheduler started")
        except ImportError as e:
            self.cron = None
            log.debug(f"CronScheduler not available: {e}")

        # ── Event Trigger Engine (event-driven task execution) ─────
        try:
            from autonomy.event_triggers import EventTriggerEngine
            self.triggers = EventTriggerEngine(self)
            self.triggers.start()
            self.triggers.register_as_tool(self.executor.registry)
            log.info("⚡ EventTriggerEngine started")
        except ImportError as e:
            self.triggers = None
            log.debug(f"EventTriggerEngine not available: {e}")

        # WebUI server reference (set when web mode starts)
        self._webui_push = None

        # Proactive thread
        self._proactive_thread = None

        # MCP Server (expose OpenAGI to Claude Code/Cursor)
        try:
            from safety.mcp_server import start_mcp_background
            if os.getenv("ENABLE_MCP_SERVER", "1") == "1":
                start_mcp_background(self)
        except Exception as e:
            log.debug(f"MCP server skip: {e}")

        # Agentic RAG for intelligent memory retrieval
        try:
            from core.agentic_rag import AgenticMemoryRAG
            from core.llm_gateway import call_nvidia
            self._agentic_rag = AgenticMemoryRAG(self.memory, call_nvidia)
            log.info("🧠 Agentic RAG initialized")
        except Exception as e:
            log.warning(f"Agentic RAG not available: {e}")
            self._agentic_rag = None

        # NL → Structured query converter
        try:
            from core.nl_to_structured import register_nl_converter
            register_nl_converter(self)
            log.info("NL→Structured converter registered")
        except Exception as e:
            log.debug(f"NL converter skip: {e}")

        log.info("OpenAGI Kernel v5.7 ready")
        log.info(f"   Tools: {self.executor.registry.list_tools()}")

    # ── Main process() ─────────────────────────────────────────────────

    def process(self, user_input: str) -> str:
        user_input = (user_input or "").strip()
        if not user_input:
            return self._generate_response("(empty message)", [], None)

        # ── Security: Prompt injection detection ─────────────────────
        if self.injection_detector:
            is_inj, reason = self.injection_detector.is_injection(user_input)
            if is_inj:
                log.warning(f"[SECURITY] Blocked injection attempt: {reason}")
                self.memory.log_event("security_block", user_input[:100], {"reason": reason}, importance=0.9)
                return "I noticed that message contains patterns that violate my operational constraints."

        self.memory.log_event("user_message", user_input, importance=0.6)

        # ── 0. Auto-extract and store personal facts ──────────────────
        # Hybrid: Pattern matching + LLM extraction for declarative statements
        # Config loader cached in __init__ for performance
        if self.config_loader:
            from core.llm_gateway import call_nvidia as _call_nvidia
            extracted_facts = self.config_loader.extract_facts(user_input, _call_nvidia)
            for fact in extracted_facts:
                self._store_fact_from_config(fact, user_input)

        # ── 1. Check for pending clarification reply ─────────────────
        pending = self.memory.get_meta_knowledge("pending_clarification")
        if pending and pending.get("content", {}).get("original"):
            question = pending["content"].get("question", "")
            original = pending["content"]["original"]

            # Heuristic: is this a new command/action (not an answer)?
            is_action = any(user_input.lower().startswith(w) for w in [
                "open ", "go to", "search", "find", "show", "run", "execute",
                "build", "create", "write", "delete", "list", "get", "fetch",
                "morning", "status", "evolve", "innovate", "/mode",
                "打开", "搜索", "建立", "展示", "运行"
            ])

            if not is_action and len(user_input.split()) <= 12:
                # Likely an answer to clarification - merge context
                user_input = f"{original}. Additional context: {user_input}"
                log.info(f"[CLARIFY] Merged: {user_input[:80]}")
            else:
                # New command - clear pending, use input as-is
                log.info(f"[CLARIFY] Cleared (new action): {user_input[:50]}")

            # ALWAYS clear pending clarification
            self.memory.update_meta_knowledge("pending_clarification", {})

        # ── 2. Intent classification + context fetch (PARALLEL) ─────
        # BUG-3 FIX: Mode-aware routing override
        if hasattr(self, 'mode_manager') and str(self.mode_manager.current) == 'code':
            # In code mode, any message containing build/create/make → build_app
            code_triggers = ['build', 'create', 'make', 'write', 'generate', 'scaffold']
            if any(t in user_input.lower() for t in code_triggers):
                ctx_str = self.user_ctx.build_context_string() if self.user_ctx else ""
                log.info(f"[CODE MODE] Routing bypass: {user_input[:50]}")
                return self._run_action(user_input, {'intent':'action', 'action':'build_app', 'parameters':{'description': user_input}}, ctx_str)

        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            classify_future = pool.submit(self.semantic.classify_intent, user_input)
            ctx_future = pool.submit(
                self.user_ctx.build_context_string if self.user_ctx else lambda: ""
            )
            intent = classify_future.result(timeout=5)
            ctx_str = ctx_future.result(timeout=3) if self.user_ctx else ""
        log.info(f"[INTENT] {intent}")
        intent_type = intent.get('intent', 'unknown')
        action_name = intent.get('action', 'conversation') if intent_type == 'action' else 'conversation'
        self._emit_thinking(f"Intent: {intent_type} → {action_name}")

        # ── 3. Depth analysis (skip for short/simple inputs) ─────────
        # Skip for: action intents, short inputs (< 6 words), greetings
        should_analyze_depth = (
            intent.get("intent") == "conversation"
            and len(user_input.split()) > 6
            and not any(w in user_input.lower() for w in ["hi", "hello", "hey", "ok", "ok", "yes", "no", "thanks", "好", "谢", "嗯", "你好"])
        )
        if should_analyze_depth:
            needs_clarify, question = self.semantic.should_clarify(user_input)
            if needs_clarify and question:
                self.memory.update_meta_knowledge(
                    "pending_clarification",
                    {"original": user_input, "question": question}
                )
                self.memory.log_event("clarification_request", question, importance=0.5)
                return question

        # ── 4. Execute action or generate conversation response ─────
        if intent.get("intent") == "action":
            return self._run_action(user_input, intent, ctx_str)
        else:
            return self._generate_response(user_input, self.history[-MAX_HISTORY_TURNS*2:], ctx_str)

    def _run_action(self, user_input: str, intent: dict, ctx_str: str = "") -> str:
        """Execute tool, then generate NVIDIA response with result context."""
        import concurrent.futures
        action = intent.get("action")
        params = intent.get("parameters", {})
        self._emit_thinking(f"Executing: {action}({list(params.keys())})")

        # Extended timeouts for slow operations
        TIMEOUTS = {
            "innovate": 90,
            "evolve": 90,
            "dag_execute": 120,
            "invent_tool": 90,
            "reason": 60,
            "browser_workflow": 120,
            "book_flight": 120,
            "computer_do": 90,
        }
        timeout = TIMEOUTS.get(action, 30)

        # Auto-screenshot for complex computer/browser tasks
        VISUAL_TASKS = {"computer_do", "browser_workflow", "book_flight", "browser_do", "browser_navigate"}
        should_screenshot = action in VISUAL_TASKS and self.computer
        screenshot_before = None
        if should_screenshot:
            try:
                screenshot_before = self.computer.screenshot()
                log.info(f"[AUTO-SS] Before screenshot: {screenshot_before}")
            except Exception:
                pass

        # Execute with timeout
        def execute_tool():
            return self.executor.execute({"action": action, "parameters": params})

        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(execute_tool)
            try:
                result = future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                return f"⏱️ `{action}` timed out after {timeout}s. Try a more specific request."
            except Exception as e:
                return f"❌ `{action}` failed: {str(e)[:200]}"

        log.info(f"[TOOL] {action} → success={result.get('success')}")
        self._emit_thinking(f"Tool: {'✓ success' if result.get('success') else '✗ failed'}")

        # Auto-screenshot after visual tasks
        if should_screenshot and result.get("success"):
            try:
                import time
                time.sleep(1)  # Let UI settle
                screenshot_after = self.computer.screenshot()
                # Analyze what changed using vision
                if screenshot_after and self.vision:
                    from core.llm_gateway import call_vision
                    description = call_vision(
                        [{"role": "user", "content": f"Briefly describe what was accomplished on screen after: '{user_input}'. 1-2 sentences."}],
                        image_path=screenshot_after,
                        max_tokens=100
                    )
                    result["screenshot"] = screenshot_after
                    result["visual_summary"] = description
                    # Push screenshot preview to WebUI
                    if hasattr(self, '_webui_push') and self._webui_push:
                        self._webui_push(f"📸 Progress: {description}")
                    log.info(f"[AUTO-SS] After screenshot taken")
            except Exception as e:
                log.debug(f"Auto-screenshot failed: {e}")

        # Goal auto-tick: check if this action completes any pending goal
        self._try_auto_complete_goal(user_input, result)

        # Build context for NVIDIA response
        mem_ctx = self.memory.get_relevant_memory_context(user_input)
        full_ctx = self.semantic.build_response_context(
            user_input, result, mem_ctx, ctx_str
        )

        # NVIDIA generates the response
        response = self._generate_response(user_input, self.history[-6:], full_ctx)
        self._update_history(user_input, response)
        return response

    def _run_innovate_with_timeout(self, user_input: str, params: dict) -> str:
        """Run innovate tool with timeout and progress updates."""
        import concurrent.futures
        from core.llm_gateway import send_telegram_alert

        # Send progress update for Telegram
        send_telegram_alert("🧠 Starting innovation process...")

        def run_innovate():
            result = self.executor.execute({"action": "innovate", "parameters": params})
            return result

        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_innovate)
                # 90 second timeout for innovate tool
                result = future.result(timeout=90)

            if not result.get("success"):
                error = result.get("error", "Unknown error")
                return f"Innovation failed: {error}"

            # Format the solutions
            data = result.get("data", {})
            solutions = data.get("solutions", [])
            if not solutions:
                return "No solutions generated."

            # Build concise response
            lines = ["🚀 **Innovation Results**", ""]
            lines.append(f"**Problem:** {data.get('problem', user_input)}")
            lines.append(f"**Solutions found:** {len(solutions)}\n")

            for i, sol in enumerate(solutions[:3], 1):
                lines.append(f"**{i}. {sol.get('solution', 'Solution')}**")
                lines.append(f"   Mechanism: {sol.get('mechanism', 'N/A')}")
                lines.append(f"   Novelty: {sol.get('novelty_score', 0):.0%} | Feasibility: {sol.get('feasibility', 0):.0%}")
                lines.append(f"   Why non-obvious: {sol.get('why_non_obvious', 'Innovative approach')}")
                lines.append("")

            return "\n".join(lines)

        except concurrent.futures.TimeoutError:
            log.error("Innovate timed out after 90s")
            return "⏱️ Innovation timed out. The problem was too complex. Try a more specific prompt."
        except Exception as e:
            log.error(f"Innovate error: {e}")
            return f"❌ Error during innovation: {str(e)[:200]}"

    def _generate_response(self, user_input: str, history: list, context: str = None, stream_callback=None) -> str:
        """All prose comes from NVIDIA. Groq never generates responses.
        If stream_callback provided, calls it with each chunk for Web UI streaming."""
        system = SYSTEM_PROMPT

        if context:
            system += f"\n\n{context}"

        if self.user_ctx:
            system += f"\n\n{self.user_ctx.build_context_string()}"

        mem_ctx = self._get_memory_ctx(user_input)
        if mem_ctx:
            system += f"\n\n{mem_ctx}"

        # Inject stored user facts into system prompt
        try:
            user_name = self.memory.get_meta_knowledge("user_name")
            if user_name and user_name.get("content"):
                name = user_name["content"]
                system += f"\n\nUSER FACT: The user's name is {name}. Use their name naturally in responses."
            user_job = self.memory.get_meta_knowledge("user_job")
            if user_job and user_job.get("content"):
                job = user_job["content"]
                system += f"\nUSER FACT: They work as/at: {job}."
            user_location = self.memory.get_meta_knowledge("user_location")
            if user_location and user_location.get("content"):
                location = user_location["content"]
                system += f"\nUSER FACT: They are located in: {location}."
        except Exception:
            pass

        messages = [{"role": "system", "content": system}]
        messages += history
        messages.append({"role": "user", "content": user_input})

        # Stream callback prevents long waits in Web UI
        response = ""
        import time
        start = time.time()

        if stream_callback:
            # Streaming mode for Web UI - chunks sent immediately
            try:
                for chunk in call_nvidia_streaming(messages, max_tokens=800, temperature=0.6):
                    response += chunk
                    stream_callback(chunk)
                    if time.time() - start > 120:
                        return response + "\n\n[Truncated: response too long]"
            except Exception as e:
                log.error(f"Streaming generation failed: {e}")
                if not response:
                    response = f"系统错误: {str(e)[:200]}"
        else:
            # Non-streaming mode with timeout protection
            import concurrent.futures
            try:
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(call_nvidia, messages, max_tokens=800, temperature=0.6)
                    while not future.done():
                        elapsed = time.time() - start
                        if elapsed > 5 and elapsed < 10:
                            log.info("[NVIDIA] Still thinking...")
                        if elapsed > 120:
                            break
                        time.sleep(0.5)
                    if future.done():
                        response = future.result(timeout=5)
                    else:
                        raise concurrent.futures.TimeoutError()
            except concurrent.futures.TimeoutError:
                log.error("NVIDIA timeout after 120s")
                response = "抱歉，这个问题比较复杂，处理时间超出了预期。请尝试一个更具体的问题。"
            except Exception as e:
                log.error(f"NVIDIA call failed: {e}")
                response = f"系统错误: {str(e)[:200]}"

        self._update_history(user_input, response)
        self.memory.log_event("assistant_response", response[:500], importance=0.4)

        # TTS in background thread (skip if streaming - Web UI handles its own TTS)
        if self.voice and not stream_callback:
            def speak_async(text):
                try:
                    self.voice.speak(text)
                except:
                    pass
            threading.Thread(target=speak_async, args=(response,), daemon=True).start()

        return response


    def _try_auto_complete_goal(self, user_input: str, result: dict):
        """Check if completed action matches any pending goal. Auto-mark it complete if so."""
        if not result.get("success"):
            return
        try:
            from core.goal_persistence import load_goal_queue, update_goal_status
            from core.llm_gateway import call_groq_router
            import re, json
            goals = load_goal_queue()
            pending = [g for g in goals if g.get("status") == "pending"]
            if not pending:
                return
            # Quick check: does this action relate to any pending goal?
            goals_text = "\n".join(f"{g['id']}: {g['description'][:60]}" for g in pending[:5])
            prompt = f"""Did this user action complete any pending goal?
User did: "{user_input}"
Result: {"success" if result.get("success") else "failed"}
Pending goals: {goals_text}
Return JSON: {{"completed_goal_id": "goal_id or null", "confidence": 0.0-1.0}}
Only mark complete if clearly and directly accomplished."""
            raw = call_groq_router([{"role": "user", "content": prompt}], max_tokens=80)
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                data = json.loads(m.group(0))
                goal_id = data.get("completed_goal_id")
                confidence = data.get("confidence", 0)
                if goal_id and confidence >= 0.7:
                    update_goal_status(goal_id, "completed", f"Auto-completed by: {user_input[:80]}", memory=self.memory)
                    log.info(f"[GOAL] Auto-ticked: {goal_id} (confidence={confidence:.2f})")
                    # Notify WebUI
                    if hasattr(self, '_webui_push') and self._webui_push:
                        goal = next((g for g in pending if g["id"] == goal_id), None)
                        if goal:
                            self._webui_push(f"✅ Goal completed: {goal['description'][:60]}")
        except Exception as e:
            log.debug(f"Goal auto-tick failed: {e}")

    def _emit_thinking(self, step: str):
        """Push a thinking step to WebUI during processing."""
        log.info(f"[THINKING] {step[:60]}")
        if hasattr(self, '_webui_push') and self._webui_push:
            self._webui_push(f"__THINKING__:{step}")

    # ── Helpers ─────────────────────────────────────────────────────

    def _store_fact_from_config(self, fact: dict, original_text: str) -> None:
        """Store a fact extracted from config_loader."""
        fact_type = fact.get("type")
        value = fact.get("value", "").strip()
        method = fact.get("method", "unknown")

        if not value:
            return

        # Map fact types to meta_knowledge keys
        META_KEYS = {
            "name": ("user_name", "user_fact"),
            "job": ("user_job", "user_fact"),
            "location": ("user_location", "user_fact"),
            "preference": ("user_preference", "user_fact"),
            "identity": ("user_identity", "user_fact"),
        }

        meta_key, event_type = META_KEYS.get(fact_type, (f"user_{fact_type}", "user_fact"))
        importance = 0.9 if fact_type == "name" else 0.8 if fact_type == "job" else 0.7

        self.memory.update_meta_knowledge(meta_key, value)
        self.memory.log_event(
            event_type,
            f"user {fact_type}: {value} (via {method})",
            importance=importance
        )
        log.info(f"[MEMORY] Stored user {fact_type} ({method}): {value}")

    def _store_personal_fact(self, text: str) -> None:
        """Extract and persist personal facts from declarative statements."""
        import re
        # Name patterns - capture full names like "Tan Ming Jing"
        name_m = re.search(r"(?:my name is|call me|you can call me|i'm|i am)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)", text, re.I)
        if name_m:
            name = name_m.group(1).strip()
            self.memory.update_meta_knowledge("user_name", name)
            self.memory.log_event("user_fact", f"user name: {name}", importance=0.9)
            log.info(f"[MEMORY] Stored user name: {name}")
            return
        # Job patterns
        job_m = re.search(r"(?:i work (?:at|for|as)|i am a|i'm a)\s+(.+?)(?:\.|,|$)", text, re.I)
        if job_m:
            job = job_m.group(1).strip()
            self.memory.update_meta_knowledge("user_job", job)
            self.memory.log_event("user_fact", f"user job: {job}", importance=0.8)
            log.info(f"[MEMORY] Stored user job: {job}")
            return
        # Location patterns
        loc_m = re.search(r"(?:i live in|i'm from|i'm in)\s+(.+?)(?:\.|,|$)", text, re.I)
        if loc_m:
            location = loc_m.group(1).strip()
            self.memory.update_meta_knowledge("user_location", location)
            self.memory.log_event("user_fact", f"user location: {location}", importance=0.7)
            log.info(f"[MEMORY] Stored user location: {location}")
        # Chinese name patterns
        cn_name_m = re.search(r"(?:我叫|你可以叫我)\s+(.{2,8})?", text)
        if cn_name_m:
            name = cn_name_m.group(1).strip()
            self.memory.update_meta_knowledge("user_name", name)
            self.memory.log_event("user_fact", f"user name (cn): {name}", importance=0.9)
            log.info(f"[MEMORY] Stored user name: {name}")

    def _get_memory_ctx(self, query: str) -> str:
        """Smart memory injection with Agentic RAG."""
        # Use Agentic RAG if available (v5.4+)
        if hasattr(self, '_agentic_rag') and self._agentic_rag:
            try:
                # FIX: was self.mode, now self.mode_manager
                is_conversation = False
                if hasattr(self, 'mode_manager') and self.mode_manager:
                    is_conversation = str(self.mode_manager.current).lower() in ('auto', 'conversation')
                context, meta = self._agentic_rag.retrieve(
                    query,
                    max_budget_ms=200 if is_conversation else 100
                )
                if context:
                    return context
            except Exception as e:
                log.debug(f"Agentic RAG failed, falling back: {e}")

        # Fallback to legacy retrieval
        return self.memory.get_relevant_memory_context(query)

    def _update_history(self, user_input: str, response: str):
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": response})
        # Keep history bounded
        if len(self.history) > MAX_HISTORY_TURNS * 2:
            self.history = self.history[-(MAX_HISTORY_TURNS * 2):]
        # Persist to session storage
        if hasattr(self, '_current_session_id') and self._current_session_id:
            self.memory.add_session_message(self._current_session_id, "user", user_input)
            self.memory.add_session_message(self._current_session_id, "assistant", response)
            # Auto-title after first exchange
            msgs = self.memory.get_session_messages(self._current_session_id)
            if len(msgs) == 2:
                self.memory.auto_title_session(self._current_session_id, user_input)

            self.memory.auto_title_session(self._current_session_id, user_input)

    def new_chat(self) -> str:
        """Start a new chat session. Memory shared. History reset."""
        self.history.clear()
        self._current_session_id = self.memory.create_session("New Chat")
        log.info(f"[SESSION] New session: {self._current_session_id}")
        return self._current_session_id

    def load_session(self, session_id: str) -> bool:
        """Load a previous chat session into active history."""
        messages = self.memory.get_session_messages(session_id, limit=50)
        if not messages:
            return False
        self.history = [{"role": m["role"], "content": m["content"]} for m in messages]
        self._current_session_id = session_id
        log.info(f"[SESSION] Loaded session: {session_id} ({len(messages)} messages)")
        return True
    def _status_report(self) -> str:
        tools = self.executor.registry.list_tools()
        pending = get_pending_count()
        recent = self.memory.get_recent_timeline(limit=3)
        recent_str = "; ".join(r.get("content", "")[:40] for r in recent)
        modules = []
        if self.proactive: modules.append("Proactive")
        if self.will: modules.append("Will")
        if self.habits: modules.append("Habits")
        if self.meta: modules.append("Meta")
        if self.causal: modules.append("Causal")
        if self.planner: modules.append("Planner")
        if self.evolution: modules.append("Evolution")
        if self.inventor: modules.append("Inventor")
        if self.dag: modules.append("DAG")
        if self.subagents: modules.append("Subagents")
        if self.vision: modules.append("Vision")
        if self.computer: modules.append("Computer")
        if self.browser: modules.append("Browser")
        if self.webui: modules.append("WebUI")
        if self.chronos: modules.append("Chronos")
        return (
            f"**OpenAGI Status**\n"
            f"Tools: {len(tools)} registered\n"
            f"Modules: {', '.join(modules) or 'none'}\n"
            f"Pending goals: {pending}\n"
            f"Recent: {recent_str}\n"
            f"Voice: {'✅' if self.voice else '❌'}\n"
            f"Google: {'✅' if self.google else '❌'}\n"
            f"WorldMonitor: {'✅' if self.worldmonitor else '❌'}"
        )

    def _list_goals(self) -> str:
        goals = load_goal_queue()
        if not goals:
            return "No pending goals."
        lines = [f"{i+1}. [{g['status']}] {g['description']}" for i, g in enumerate(goals[:10])]
        return "**Goals:**\n" + "\n".join(lines)

    # ── Run modes ───────────────────────────────────────────────────

    def run_telegram(self):
        """Telegram bot mode."""
        import threading
        from core.llm_gateway import send_telegram_alert, get_telegram_updates

        # Start ProactiveEngine only in Telegram mode
        if self.proactive:
            self.proactive.start()
            log.info("🔁 ProactiveEngine started (Telegram mode)")

        log.info("📱 Telegram mode started")
        send_telegram_alert("✅ OpenAGI online. Send me a message.")

        # Initialize call mode for voice messages
        try:
            from interfaces.call_mode import CallMode
            call_mode = CallMode(self)
            log.info("📞 CallMode initialized")
        except ImportError as e:
            log.debug(f"CallMode not available: {e}")
            call_mode = None

        offset = None
        while True:
            try:
                updates = get_telegram_updates(offset)
                for update in updates:
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})

                    # Handle voice messages
                    if msg.get("voice") and call_mode:
                        file_id = msg["voice"]["file_id"]
                        send_telegram_alert("🎤 Processing voice message...")
                        try:
                            response = call_mode.process_voice_message(file_id)
                            send_telegram_alert(response[:4000])
                        except Exception as e:
                            log.error(f"Voice processing error: {e}")
                            send_telegram_alert(f"Voice processing failed: {str(e)[:200]}")
                        continue

                    text = msg.get("text", "").strip()
                    if text:
                        log.info(f"[TG] Received: {text[:60]}")
                    # Check keyword triggers
                    if hasattr(self, 'triggers') and self.triggers:
                        self.triggers.check_keyword(text)
                        # Check if innovate tool might be invoked
                        is_innovate = "innovate" in text.lower() or "invent" in text.lower()
                        if is_innovate:
                            send_telegram_alert("⚡ Innovation in progress... (this may take 30-60s)")
                        else:
                            send_telegram_alert("⚡ Processing...")
                        response = self.process(text)
                        send_telegram_alert(response[:4000])
            except KeyboardInterrupt:
                break
            except Exception as e:
                log.error(f"Telegram loop error: {e}")
                time.sleep(5)

    def run_voice_mode(self):
        """Continuous voice mode — wake word → transcribe → process → speak."""
        if not self.voice:
            log.error("Voice engine not available")
            return

        log.info("🎤 Voice mode started")

        if self.jarvis:
            try:
                briefing = self.jarvis.morning_briefing()
                log.info(f"Briefing: {briefing[:80]}")
            except Exception:
                pass

        def voice_callback(transcript: str):
            log.info(f"[VOICE] Heard: {transcript}")
            response = self.process(transcript)
            log.info(f"[VOICE] Responding: {response[:60]}")
            # speak() is called inside process() if voice is set

        self.voice.start_continuous_mode(callback=voice_callback)

        # Block main thread
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    def run_web(self):
        """Web UI mode - auto builds React frontend and starts backend."""
        try:
            import sys
            import subprocess
            from pathlib import Path

            project_root = Path(__file__).parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

            # ─── AUTO BUILD FRONTEND ────────────────────────────────────
            frontend_dir = project_root / "frontend"
            frontend_dist = frontend_dir / "dist"

            if frontend_dir.exists():
                print("\n" + "="*60)
                print("  🚀 OpenAGI Web UI")
                print("="*60)

                # Check if dist exists, if not build
                if not frontend_dist.exists():
                    print("\n📦 Building React frontend (first time only)...")
                    try:
                        # Check if node_modules exists
                        if not (frontend_dir / "node_modules").exists():
                            print("   Installing npm dependencies...")
                            subprocess.run(
                                ["npm", "install"],
                                cwd=str(frontend_dir),
                                capture_output=True,
                                check=True
                            )

                        # Build frontend
                        result = subprocess.run(
                            ["npm", "run", "build"],
                            cwd=str(frontend_dir),
                            capture_output=True,
                            text=True,
                            check=True
                        )
                        print("   ✅ Frontend built successfully!")
                    except subprocess.CalledProcessError as e:
                        print(f"   ❌ Frontend build failed: {e.stderr}")
                        raise
                    except FileNotFoundError:
                        print("   ⚠️  npm not found. Please install Node.js")
                        raise
                else:
                    print("   ✅ Using existing frontend build")

                print("\n🔌 Starting backend server on http://localhost:8765")
                print("   WebSocket: ws://localhost:8765/ws")
                print("   Frontend: http://localhost:8765")
                print("\n" + "="*60 + "\n")
            else:
                print("⚠️  frontend/ directory not found")

            # ─── START BACKEND ──────────────────────────────────────────
            from interfaces.webui_server import WebUIServer
            self.webui = WebUIServer(self)
            self.webui.start()  # This blocks on uvicorn.run()

        except ImportError as e:
            log.error(f"webui_server import failed: {e}")
            log.info("Install dependencies: pip install fastapi uvicorn qrcode[pil]")
            raise
        except Exception as e:
            log.error(f"Web UI startup failed: {e}")
            raise

    def run_cli(self):
        """Interactive CLI mode."""
        print("\n" + "="*50)
        print("  OpenAGI v5.0 — CLI Mode")
        print("  Commands: 'morning briefing', 'status', 'goals', 'exit'")
        print("="*50 + "\n")

        while True:
            try:
                u = input("You > ").strip()
                if u.lower() in ("exit", "quit", "q", "bye"):
                    print("OpenAGI shutting down.")
                    break
                if u:
                    response = self.process(u)
                    print(f"\nAGI > {response}\n")
            except (KeyboardInterrupt, EOFError):
                break

        self.shutdown()

    def shutdown(self):
        if self.proactive:
            self.proactive.stop()
        if hasattr(self, 'chronos'):
            self.chronos.stop()
        if self.voice:
            self.voice.stop()
        if self.browser:
            self.browser.close()
        self.memory.close()
        log.info("OpenAGI shutdown complete")


# ── Entry point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "auto"
    kernel = Kernel()

    if mode == "voice":
        kernel.run_voice_mode()
    elif mode == "web":
        kernel.run_web()
    elif mode == "cli":
        kernel.run_cli()
    elif mode == "telegram" or os.getenv("TELEGRAM_BOT_TOKEN"):
        kernel.run_telegram()
    else:
        kernel.run_cli()

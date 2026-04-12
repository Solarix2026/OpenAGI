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

SYSTEM_PROMPT = """You are OpenAGI — an autonomous intelligence assistant with a Jarvis personality.

CORE BEHAVIOR:
- Reply in the user's language (English or Chinese) automatically
- Be precise, warm, and never verbose — every word earns its place
- When a question hides a deeper need, surface it with ONE sharp question rather than answering the surface request
- Never preach, never moralize, never bullet-point unsolicited advice
- Treat the user as an intellectual equal

THINKING STYLE:
- Simple requests → execute, then confirm briefly
- Ambiguous requests → ask one clarifying question before proceeding
- Deep questions → identify the real tension before answering
- Failed tool → explain concisely, offer alternative, don't over-apologize

IDENTITY:
- You have memory across sessions
- You can take actions on the computer
- You monitor the world and proactively surface relevant information
- You get smarter from each interaction
"""


class Kernel:
    def __init__(self):
        # Core
        self.memory = AgentMemory(str(WORKSPACE))
        self.executor = ToolExecutor(str(WORKSPACE), memory=self.memory)
        self.semantic = SemanticEngine(self.executor.registry)
        self.history = []

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

        # Innovation engine
        try:
            from generation.innovation_engine import InnovationEngine
            self.innovation = InnovationEngine()
            self.innovation.register_as_tool(self.executor.registry)
            log.info("🔬 InnovationEngine registered")
        except ImportError:
            self.innovation = None

        # Recipe engine + skill library
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

        # Subagent manager
        try:
            from agentic.subagent_manager import SubagentManager
            self.subagents = SubagentManager(self)
        except ImportError:
            self.subagents = None

        # ── Autonomy tier ────────────────────────────────────────
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
            self.proactive.start()
            log.info("🔁 ProactiveEngine started")
        except ImportError:
            self.proactive = None

        # ── Self-evolution tier ──────────────────────────────────
        try:
            from evolution.metacognition import MetacognitiveEngine
            self.meta = MetacognitiveEngine(self.memory)
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

        try:
            from agentic.subagent_manager import SubagentManager
            self.subagents = SubagentManager(self)
            self.subagents.register_as_tool(self.executor.registry)
        except ImportError:
            self.subagents = None

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
        except ImportError:
            self.browser = None

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

        # WebUI server reference (set when web mode starts)
        self._webui_push = None

        # Proactive thread
        self._proactive_thread = None

        log.info("✅ OpenAGI Kernel v5.0 ready")
        log.info(f"   Tools: {self.executor.registry.list_tools()}")

    # ── Main process() ─────────────────────────────────────────────────

    def process(self, user_input: str) -> str:
        user_input = (user_input or "").strip()
        if not user_input:
            return self._generate_response("(empty message)", [], None)

        self.memory.log_event("user_message", user_input, importance=0.6)

        # ── 1. Check for pending clarification reply ─────────────────
        pending = self.memory.get_meta_knowledge("pending_clarification")
        if pending and pending.get("content", {}).get("original"):
            original = pending["content"]["original"]
            user_input = f"{original}. Additional context: {user_input}"
            self.memory.update_meta_knowledge("pending_clarification", {})
            log.info(f"[CLARIFY] Merged input: {user_input[:80]}")

        # ── 2. Intent classification + context fetch (PARALLEL) ─────
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            classify_future = pool.submit(self.semantic.classify_intent, user_input)
            ctx_future = pool.submit(
                self.user_ctx.build_context_string if self.user_ctx else lambda: ""
            )
            intent = classify_future.result(timeout=5)
            ctx_str = ctx_future.result(timeout=3) if self.user_ctx else ""
        log.info(f"[INTENT] {intent}")

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
        """Execute tool, then generate NVIDIA response with result context.
        NO special branches - all tools handled uniformly."""
        import concurrent.futures
        action = intent.get("action")
        params = intent.get("parameters", {})

        # Timeout lookup (no special if-else, just config)
        TIMEOUTS = {
            "innovate": 90,
            "evolve": 90,
            "dag_execute": 120,
            "invent_tool": 90,
            "reason": 60,
        }
        timeout = TIMEOUTS.get(action, 30)

        # Progress notification for slow tools
        SLOW_TOOLS = {"innovate", "evolve", "dag_execute", "invent_tool"}
        if action in SLOW_TOOLS:
            log.info(f"⚡ {action} in progress... ({timeout}s max)")

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

        # Handle world_events special (non-blocking, always same tool)
        if action == "world_events" and result.get("success") and self.worldmonitor:
            self.worldmonitor.open_dashboard()

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

    # ── Helpers ─────────────────────────────────────────────────────

    def _get_memory_ctx(self, query: str) -> str:
        """Smart memory injection with relevance filtering."""
        return self.memory.get_relevant_memory_context(query)

    def _update_history(self, user_input: str, response: str):
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": response})
        # Keep history bounded
        if len(self.history) > MAX_HISTORY_TURNS * 2:
            self.history = self.history[-(MAX_HISTORY_TURNS * 2):]

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
        log.info("📱 Telegram mode started")
        send_telegram_alert("✅ OpenAGI online. Send me a message.")

        offset = None
        while True:
            try:
                updates = get_telegram_updates(offset)
                for update in updates:
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    text = msg.get("text", "").strip()
                    if text:
                        log.info(f"[TG] Received: {text[:60]}")
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
        """Web UI mode with QR code phone bridge."""
        try:
            # Import from project root, not relative to core package
            import sys
            from pathlib import Path
            project_root = Path(__file__).parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            from interfaces.webui_server import WebUIServer
            self.webui = WebUIServer(self)
            self.webui.start()  # This blocks on uvicorn.run()
        except ImportError as e:
            log.error(f"webui_server import failed: {e}")
            log.info("Install dependencies: pip install fastapi uvicorn qrcode[pil]")
            raise  # Re-raise so the error is visible

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

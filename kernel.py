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

from llm_gateway import call_nvidia, call_groq_router, send_telegram_alert, get_telegram_updates
from memory_core import AgentMemory
from tool_executor import ToolExecutor
from semantic_engine import SemanticEngine
from goal_persistence import load_goal_queue, add_to_goal_queue, get_pending_count

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
            from user_context import UserContextProvider
            self.user_ctx = UserContextProvider()
        except ImportError:
            self.user_ctx = None

        # Jarvis persona
        try:
            from jarvis_persona import JarvisPersona
            self.jarvis = JarvisPersona(self.memory)
        except ImportError:
            self.jarvis = None

        # Voice
        try:
            from voice_engine import VoiceEngine
            self.voice = VoiceEngine()
            if self.jarvis:
                self.jarvis.voice = self.voice
        except ImportError:
            self.voice = None
            log.info("Voice engine not available (install pvporcupine/edge-tts)")

        # Google integration
        try:
            from google_integration import GoogleIntegration
            self.google = GoogleIntegration()
            if self.jarvis:
                self.jarvis.google = self.google
        except ImportError:
            self.google = None

        # WorldMonitor
        try:
            from worldmonitor_client import WorldMonitorClient
            self.worldmonitor = WorldMonitorClient()
            if self.jarvis:
                self.jarvis.worldmonitor = self.worldmonitor
            # Register world_events tool (already in executor, but wire briefing)
        except ImportError:
            self.worldmonitor = None

        # Innovation engine
        try:
            from innovation_engine import InnovationEngine
            self.innovation = InnovationEngine()
            self.innovation.register_as_tool(self.executor.registry)
            log.info("🔬 InnovationEngine registered")
        except ImportError:
            self.innovation = None

        # Recipe engine + skill library
        try:
            from recipe_engine import RecipeEngine
            from skill_library import SkillLibrary
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
            from subagent_manager import SubagentManager
            self.subagents = SubagentManager(self)
        except ImportError:
            self.subagents = None

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

        # ── 2. Special commands ──────────────────────────────────────
        lower = user_input.lower().strip()
        if lower in ("morning briefing", "早安简报", "morning brief"):
            if self.jarvis:
                return self.jarvis.morning_briefing()
        if lower in ("status", "状态"):
            return self._status_report()
        if lower in ("list goals", "我的目标", "目标"):
            return self._list_goals()

        # ── 3. Intent classification (Groq router) ──────────────────
        intent = self.semantic.classify_intent(user_input)
        log.info(f"[INTENT] {intent}")

        # ── 4. Depth analysis for conversation + complex actions ─────
        if intent.get("intent") == "conversation" and len(user_input) > 15:
            needs_clarify, question = self.semantic.should_clarify(user_input)
            if needs_clarify and question:
                self.memory.update_meta_knowledge(
                    "pending_clarification",
                    {"original": user_input, "question": question}
                )
                self.memory.log_event("clarification_request", question, importance=0.5)
                return question

        # ── 5. Execute action or generate conversation response ──────
        if intent.get("intent") == "action":
            return self._run_action(user_input, intent)
        else:
            return self._generate_response(user_input, self.history[-MAX_HISTORY_TURNS*2:], None)

    def _run_action(self, user_input: str, intent: dict) -> str:
        """Execute tool, then generate NVIDIA response with result context."""
        action = intent.get("action")
        params = intent.get("parameters", {})

        # Special: world_events → WorldMonitor briefing
        if action == "world_events" and self.worldmonitor:
            events = self.worldmonitor.get_events()
            ctx_str = self.user_ctx.build_context_string() if self.user_ctx else ""
            briefing = self.worldmonitor.summarize_for_briefing(events, ctx_str)
            self.worldmonitor.open_dashboard()
            if self.voice:
                try:
                    self.voice.speak(briefing)
                except Exception:
                    pass
            response = briefing + f"\n\n📡 WorldMonitor dashboard opened."
            self._update_history(user_input, response)
            return response

        # Execute tool
        result = self.executor.execute({"action": action, "parameters": params})
        log.info(f"[TOOL] {action} → success={result.get('success')}")

        # Build context for NVIDIA response
        mem_ctx = self._get_memory_ctx(user_input)
        ctx_str = self.user_ctx.build_context_string() if self.user_ctx else ""
        full_ctx = self.semantic.build_response_context(
            user_input, result, mem_ctx, ctx_str
        )

        # NVIDIA generates the response
        response = self._generate_response(user_input, self.history[-6:], full_ctx)
        self._update_history(user_input, response)
        return response

    def _generate_response(self, user_input: str, history: list, context: str = None) -> str:
        """All prose comes from NVIDIA. Groq never generates responses."""
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

        response = call_nvidia(messages, max_tokens=800)
        self._update_history(user_input, response)
        self.memory.log_event("assistant_response", response[:500], importance=0.4)

        if self.voice:
            try:
                self.voice.speak(response)
            except Exception:
                pass

        return response

    # ── Helpers ─────────────────────────────────────────────────────

    def _get_memory_ctx(self, query: str) -> str:
        try:
            results = self.memory.search_events(query, limit=3)
            snippets = [r.get("content", "")[:150] for r in results if r.get("content")]
            if snippets:
                return "Relevant memory:\n" + "\n".join(f"- {s}" for s in snippets)
        except Exception:
            pass
        return ""

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
        return (
            f"**OpenAGI Status**\n"
            f"Tools: {len(tools)} registered\n"
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
        from llm_gateway import send_telegram_alert, get_telegram_updates
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
            from webui_server import WebUIServer
            WebUIServer(self).start()
        except ImportError:
            log.error("webui_server.py not found. Build it first.")

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

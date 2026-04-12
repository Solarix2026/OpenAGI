# OpenAGI — Autonomous Intelligence System

> An L4 autonomous AI agent built on NVIDIA NIM + Groq, running locally on Windows.
> Jarvis-style personality. Self-evolving. Computer-controlling.

## Architecture

```
User Input
    ↓
Groq 8B (Router — JSON classification, <300ms)
    ↓
Intent: action → ToolExecutor → NVIDIA NIM (response)
Intent: conversation → SemanticEngine depth check → NVIDIA NIM

Memory: SQLite (episodic) + FAISS (semantic vector search)
Autonomy: ProactiveEngine + WillEngine running in background
Evolution: EvolutionEngine + ToolInvention + CHRONOS_REVERIE (3am)
```

## Capability Level: L4 (targeting L5)

| Dimension | Score | Notes |
|---|---|---|
| Conversation | 4.5/5 | NVIDIA NIM, context-aware, bilingual |
| Memory | 4/5 | FAISS+SQLite RAG, cross-session |
| Proactive | 3.5/5 | Background loop, world events |
| Computer Control | 3/5 | Vision+pyautogui, Playwright |
| Self-Evolution | 3/5 | Gap→Curriculum→Test loop |
| Innovation | 3/5 | First principles + analogical |
| Voice | 3/5 | Groq Whisper + edge-tts |
| Web UI | 3/5 | FastAPI + WebSocket + QR |

## Quick Start

```bash
# 1. Install
setup.bat

# 2. Add API keys to .env
# GROQ_API_KEY=xxx
# NVIDIA_API_KEY=nvidia_xxx

# 3. Run
python kernel.py              # CLI mode
python kernel.py telegram     # Telegram bot
python kernel.py web          # Web UI + QR phone
python kernel.py voice        # Voice/Jarvis mode
```

## Project Structure

```
OpenAGI/
├── core/                    # Brain + memory
│   ├── kernel.py           # Main orchestrator
│   ├── llm_gateway.py      # NVIDIA/Groq routing
│   ├── memory_core.py      # SQLite + FAISS
│   ├── semantic_engine.py  # Intent understanding
│   ├── tool_registry.py    # Tool registration
│   ├── tool_executor.py    # Tool execution
│   ├── user_context.py     # Geo + weather
│   └── goal_persistence.py # Goal queue
│
├── autonomy/                # Proactive + will
│   ├── will_engine.py      # Conatus/Telos/Dialectic
│   ├── proactive_engine.py # Background loop
│   ├── beep_filter.py      # Notification filter
│   ├── habit_profiler.py   # User pattern learning
│   └── chronos_reverie.py  # Nightly review
│
├── evolution/              # Self-improvement
│   ├── metacognition.py    # Self-analysis
│   ├── causal_engine.py   # Root cause analysis
│   ├── strategic_planner.py
│   ├── evolution_engine.py
│   ├── reasoning_engine.py # CoT/ToT/Debate
│   └── tool_invention.py  # Dynamic tool creation
│
├── agentic/               # Workflow orchestration
│   ├── dag_workflow.py    # Parallel execution
│   ├── subagent_manager.py
│   ├── recipe_engine.py
│   └── skill_library.py   # YAML skills
│
├── control/               # Computer + browser
│   ├── vision_engine.py   # Screen understanding
│   ├── computer_control.py # pyautogui
│   └── browser_agent.py   # Playwright
│
├── interfaces/            # Human-facing
│   ├── voice_engine.py    # STT/TTS
│   ├── webui_server.py    # Web UI + phone
│   ├── jarvis_persona.py  # Personality
│   ├── notification_hub.py
│   ├── call_mode.py       # Telegram voice
│   └── google_integration.py
│
├── generation/            # Content creation
│   ├── innovation_engine.py
│   ├── saas_builder.py    # FastAPI scaffolder
│   ├── video_deck_skill.py
│   ├── document_reader.py # Word/Excel/PDF
│   └── skill_library.py
│
├── safety/                # Guard protocols
│   ├── guard_protocols.py
│   └── plugin_api.py
│
├── routing/               # Multi-model router
│   └── multi_agent_router.py
│
├── skills/                # YAML recipes
│   ├── video_deck.yaml
│   ├── morning_brief.yaml
│   ├── code_review.yaml
│   ├── lead_tracker.yaml
│   └── saas_scaffold.yaml
│
├── workspace/             # Runtime data (gitignored)
│   ├── agent_state.db
│   └── ...
│
└── plugins/               # User plugins (gitignored)
```

## Key Files

- `core/kernel.py` — Main orchestrator
- `core/semantic_engine.py` — Intent understanding (L4: no hardcoding)
- `core/memory_core.py` — 4-tier memory (SQLite+FAISS)
- `autonomy/will_engine.py` — Autonomous motivation (Conatus/Telos/Dialectic)
- `autonomy/proactive_engine.py` — Background intelligence loop
- `evolution/evolution_engine.py` — Self-improvement cycles
- `evolution/tool_invention.py` — Dynamic tool creation
- `evolution/reasoning_engine.py` — Chain-of-Thought, Tree-of-Thought, Debate
- `control/vision_engine.py` — NVIDIA NIM screen understanding
- `interfaces/webui_server.py` — Web UI + phone bridge

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Groq API for routing |
| `NVIDIA_API_KEY` | Yes | NVIDIA NIM for generation |
| `TELEGRAM_BOT_TOKEN` | Optional | Telegram bot mode |
| `TELEGRAM_CHAT_ID` | Optional | Telegram notifications |
| `OPENWEATHER_API_KEY` | Optional | Weather data |
| `GOOGLE_CLIENT_ID` | Optional | Google Calendar/Gmail |

## License

MIT License — Copyright (c) 2026 HackerTMJ (门牌号3号)

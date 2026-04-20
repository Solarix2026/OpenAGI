# OpenAGI v5.5 — Autonomous Intelligence System (L4)

> An L4 autonomous AI agent with memory, computer control, self-evolution, proactive intelligence, and multi-agent hiring.
> Built on NVIDIA NIM + Groq. Local-first. Private. Open source.
> 
> **Company**: ApeironAI/Apeiron | **Founder**: github.com/ApeironAI-Team

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/ApeironAI-Team/OpenAGI/blob/main/LICENSE)
[![Python 3.11-3.14](https://img.shields.io/badge/python-3.11--3.14-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18-61DAFB.svg)](https://react.dev/)

---

## What's New in v5.5

| Feature | Description |
|---------|-------------|
| **Agent Hiring (MAS)** | Hire specialized AI agents: CTO, CMO, Researcher, Developer, Analyst. Each has role-specific models and tool scopes. |
| **PlanningAssistant** | AI-powered planning that breaks objectives into scheduled tasks. Auto-assigns AI-only tasks to CronScheduler. |
| **Real-time WebSocket** | Live logs, memory events, goal updates, and agent status streamed via WebSocket to React frontend. |
| **URL Reader Tool** | Extract and summarize content from any webpage or PDF using `read_url`. |
| **CronScheduler v2** | Schedule tasks with completion reminders. Natural language time parsing ("every morning at 8am"). |
| **Python 3.14 Support** | Graceful degradation on Python 3.14+ (keyword search instead of embeddings). |

---

## L4 Capability Assessment

| Dimension | OpenAGI L4 | ChatGPT | Claude | GitHub Copilot | Perplexity |
|-----------|:----------:|:-------:|:------:|:--------------:|:----------:|
| **Conversation Quality** | 4.5/5 | 5/5 | 5/5 | 2/5 | 3/5 |
| **Memory (Cross-Session)** | 5/5 | 2/5 | 2/5 | 1/5 | 1/5 |
| **Semantic Search (RAG)** | 4/5 | 3/5 | 3/5 | 1/5 | 4/5 |
| **Computer Control** | 4/5 | 1/5 | 1/5 | 1/5 | 1/5 |
| **Proactive Intelligence** | 4/5 | 1/5 | 1/5 | 1/5 | 2/5 |
| **Self-Evolution** | 3/5 | 1/5 | 1/5 | 1/5 | 1/5 |
| **Tool Invention** | 4/5 | 1/5 | 1/5 | 1/5 | 1/5 |
| **Multi-Agent System** | 5/5 | 2/5 | 2/5 | 1/5 | 1/5 |
| **Code Generation** | 4/5 | 4/5 | 4.5/5 | 5/5 | 3/5 |
| **Multi-Modal (Voice/Vision)** | 4/5 | 3/5 | 2/5 | 1/5 | 1/5 |
| **Privacy (Local-First)** | 5/5 | 1/5 | 1/5 | 1/5 | 1/5 |
| **Cost (Self-Hosted)** | 5/5 | 2/5 | 2/5 | 3/5 | 3/5 |
| **TOTAL SCORE** | **50/60** | **26/60** | **25.5/60** | **19/60** | **22/60** |

---

## Feature Comparison Matrix

| Feature | OpenAGI | ChatGPT | Claude | Goose | Devin |
|---------|:-------:|:-------:|:------:|:-----:|:-----:|
| **Open Source** | ✅ MIT | ❌ | ❌ | ✅ MIT | ❌ |
| **Self-Hosted** | ✅ Local | ❌ Cloud | ❌ Cloud | ❌ | ❌ |
| **Computer Control** | ✅ A11y + Vision | ❌ | ❌ | ⚠️ Limited | ✅ |
| **Self-Evolving** | ✅ Gap detection | ❌ | ❌ | ❌ | ❌ |
| **Memory (Episodic)** | ✅ Cross-session | ⚠️ Thread only | ⚠️ Thread only | ❌ | ❌ |
| **Vision (Screen)** | ✅ Built-in | ❌ | ❌ | ❌ | ✅ |
| **Voice Mode** | ✅ Porcupine + EdgeTTS | ❌ | ❌ | ❌ | ❌ |
| **Proactive Nudges** | ✅ Background | ❌ | ❌ | ❌ | ❌ |
| **Tool Invention** | ✅ Auto-register | ❌ | ❌ | ❌ | ❌ |
| **Multi-Agent Hiring** | ✅ AgentOrg | ⚠️ GPTs | ❌ | ❌ | ❌ |
| **Task Scheduling** | ✅ Cron + Natural Language | ❌ | ❌ | ❌ | ❌ |
| **Web Real-time UI** | ✅ React + WebSocket | ❌ | ❌ | ❌ | ❌ |
| **Recipe Engine** | ✅ YAML workflows | ❌ | ❌ | ❌ | ❌ |

---

## Architecture v5.5

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACE                          │
│  CLI │ Web IDE (React+WS) │ Telegram │ Voice (Jarvis)         │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      KERNEL v5.5                            │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Semantic   │──→│    Tool      │──→│   NVIDIA     │       │
│  │  Engine     │  │  Executor    │  │  NIM 49B     │       │
│  │ (Groq 8B)   │  │  (Registry)  │  │  Response    │       │
│  └─────────────┘  └──────────────┘  └──────────────┘       │
│         │                  │                  │            │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Memory    │  │   Computer   │  │  Proactive   │       │
│  │(SQLite+FAISS│  │   Control    │  │   Engine     │       │
│  └─────────────┘  └──────────────┘  └──────────────┘       │
│         │                  │                  │            │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   AgentOrg  │  │    Vision    │  │   Cron       │       │
│  │ (Multi-Agent│  │   Engine     │  │  Scheduler   │       │
│  └─────────────┘  └──────────────┘  └──────────────┘       │
│         │                                                     │
│  ┌─────────────┐  ┌──────────────┐                        │
│  │   Planning  │  │   Recipe     │                        │
│  │  Assistant  │  │   Engine     │                        │
│  └─────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites
- Python 3.11-3.14 (3.14 supported with graceful degradation)
- Node.js 18+ (for frontend)
- Windows 10/11 or Linux/macOS with Wine

### Installation

```bash
# 1. Clone
git clone https://github.com/ApeironAI-Team/OpenAGI.git
cd OpenAGI

# 2. Install (Windows - auto setup)
setup.bat

# 3. Configure API keys in .env
cp .env.example .env
# Edit .env:
GROQ_API_KEY=gsk_xxx
NVIDIA_API_KEY=nvapi_xxx

# 4. Run
python kernel.py web      # Web UI with real-time updates
python kernel.py cli      # Command-line mode
python kernel.py voice    # Jarvis voice mode
python kernel.py telegram # Telegram bot
```

---

## Web UI Features

### React + TypeScript Frontend
- **Live Logs**: Real-time kernel logs via WebSocket with auto-scroll
- **Memory Explorer**: Browse episodic memory, search semantically
- **Goals Dashboard**: Track goals with progress bars, task checklists
- **Agent Team**: Hire/fire AI agents, delegate tasks
- **Settings**: Configure API keys, preferences, modes
- **Real-time Updates**: All data synced via WebSocket, no polling needed

### Getting the Frontend Running
```bash
cd frontend
npm install
npm run dev        # Dev server
npm run build      # Production build
```

---

## Agent Hiring System (MAS)

Hire specialized AI agents for specific roles:

```python
# Hire a CTO for architecture decisions
hire_agent(role="CTO")

# Delegate a coding task to Developer
delegate_task(role="Developer", task="Write unit tests for auth module")

# List your team
list_agents()

# Fire an agent
fire_agent(role="Analyst")
```

### Available Roles
| Role | Model | Tool Scope |
|------|-------|------------|
| CTO | deepseek-chat | code, shell, file, browser |
| CMO | gpt-4 | websearch, research_topic |
| Researcher | gemma-3-27b | websearch, arxiv_search, worldbank_data |
| Developer | deepseek-chat | shell_command, write_file, read_file |
| Analyst | llama-3.3-nemotron | analyze_stock, worldbank_data |

---

## Task Scheduling

Schedule recurring tasks with natural language:

```python
# Schedule with natural language
schedule_task(
    task="Summarize my emails",
    when="every morning at 8am"
)

# With completion reminder
scheduler.schedule_with_reminder(
    "Weekly code review",
    natural="every friday at 5pm",
    notify_completion=True
)
```

### Supported Time Formats
- "every day at 8am"
- "every monday at 9am"
- "every 30 minutes"
- "every morning" (8am)
- "every evening" (6pm)

---

## Modes

```
/mode auto     → Default intelligent routing
/mode code     → GitHub Spark-style app builder
/mode reason   → Extended CoT with explicit thinking
/mode plan     → Multi-step planning before execution
/mode research → Deep web search + synthesis
```

---

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Windows 10/11 | Windows 11 Pro |
| RAM | 8GB | 16GB+ |
| GPU | None (CPU fallback) | NVIDIA RTX 3060+ |
| Storage | 5GB | 10GB |
| Node.js | 18+ | 20+ |

---

## API Usage

| Provider | Model | Purpose | Cost |
|----------|-------|---------|------|
| NVIDIA | Kimi K2/K2.5 | Responses (reasoning/multi-tool) | ~$0.0003/1K tokens |
| Groq | Llama 3.1 8B | Routing/JSON | ~$0.0001/1K tokens |

**Typical daily usage: $0.50-2.00** (vs $20/mo ChatGPT Plus)

---

## Project Structure

```
OpenAGI/
├── core/              # Kernel, memory, tools, gateway, semantic engine
├── autonomy/          # CronScheduler, ProactiveEngine, HabitProfiler
├── control/           # Computer control, vision, browser automation
├── agentic/           # AgentOrg (multi-agent), skill library, recipes
├── evolution/         # Self-improvement, metacognition
├── interfaces/        # WebUI server (FastAPI+WebSocket), voice, Telegram
│   ├── webui_server.py
│   └── webui_template.html
├── generation/        # SaaS builder, video deck, document reader
├── routing/           # Multi-agent router
├── safety/            # Guard protocols, MCP adapter
├── frontend/          # React 18 + TypeScript SPA
│   ├── src/pages/     # Logs, Memory, Goals, Agents, Settings
│   └── src/services/  # WebSocket, API clients
└── workspace/         # Runtime state (SQLite, FAISS, goals)
```

---

## Open Source Decision

**Recommendation: YES, open source on GitHub**

**Why:**
1. **Differentiation**: OpenAGI is genuinely advanced (L4 autonomy, multi-agent, proactive)
2. **Community**: Attracts contributors, bug reports, feature ideas
3. **Credibility**: Open source = transparent = trust
4. **Hiring**: Portfolio piece for ApeironAI team
5. **Safety**: L4 agents should be auditable

**License**: MIT (already set)
**Repo**: github.com/ApeironAI-Team/OpenAGI

---

## Compare Projects

| Project | Type | Autonomy | Multi-Agent | Web UI | Open Source |
|---------|------|----------|-------------|--------|-------------|
| **OpenAGI v5.5** | L4 Agent | ✅ High | ✅ Hire + Delegate | ✅ Real-time WS | ✅ MIT |
| Goose | AI IDE | ⚠️ Medium | ❌ | ❌ | ✅ MIT |
| Claude Code | AI IDE | ❌ Low | ❌ | ❌ | ❌ |
| Devin | AI Dev | ✅ High | ❌ | ❌ | ❌ |
| AutoGPT | L3 Agent | ⚠️ Medium | ⚠️ Limited | ❌ | ✅ MIT |

---

## Development Status

| Component | Status |
|-----------|--------|
| Core Kernel | ✅ Stable |
| WebSocket Real-time | ✅ Production |
| React Frontend | ✅ 9 Pages Complete |
| Agent Hiring | ✅ AgentOrg Ready |
| Task Scheduling | ✅ CronScheduler v2 |
| Memory System | ✅ SQLite + FAISS |
| Python 3.14 | ✅ Graceful Degradation |

**Status**: v5.5 Released ✅ | Targeting v6.0 (L5) 🚀

**Last Updated**: 2026-04-20

---

## License

MIT License — see [LICENSE](LICENSE)

Copyright (c) 2026 ApeironAI

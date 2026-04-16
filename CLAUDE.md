# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

### Setup & Installation

**Windows (Recommended)**
```bash
setup.bat
```
This creates venv, installs all dependencies, creates `.env` file, and prompts for API keys.

**Manual (Unix/Mac)**
```bash
# Install dependencies (no requirements.txt - see setup.bat for list)
pip install groq openai chromadb sentence-transformers beautifulsoup4 requests python-dotenv fastapi uvicorn websockets qrcode[pil] Pillow pyttsx3 edge-tts google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client feedparser pyyaml jinja2 pyaudio sounddevice soundfile plyer psutil faiss-cpu

# Create .env from template
cp .env.example .env
# Edit .env with your API keys (see Configuration below)
```

### Running OpenAGI

```bash
# Windows launcher (prompts for mode if none given)
run.bat [mode]

# Direct Python (Unix/any OS)
python kernel.py [mode]

# Modes:
# cli - Command-line interface (default)
# web - Web UI with QR code (port 8765)
# voice - Jarvis voice mode with wake word detection
# telegram - Telegram bot mode
```

### Testing

```bash
# Quick test suite (10 core tests with basic pass/fail)
python run_tests.py

# L4 verification suite (10 focused tests for L4 autonomy)
python test_l4_verification.py

# Comprehensive test suite (extensive coverage across all tiers)
python test_comprehensive.py

# Full test suite (complete validation)
python test_all.py

# Run a specific test function
python -c "from run_tests import *; test_tool_registry()"
python -c "from test_l4_verification import *; test_1_no_hardcode()"
```

## Configuration

**Required Environment Variables** (in `.env`):
- `GROQ_API_KEY` - Llama 3.1 8B router (classification, JSON)
- `NVIDIA_API_KEY` - Llama 3.3 Nemotron 49B (response generation)

**Key Optional Settings**:
- `WEBUI_PORT=8765` - Web server port
- `MAX_HISTORY_TURNS=8` - Conversation history depth
- `WORKSPACE=./workspace` - Agent state and memory storage
- `USER_CITY`, `USER_COUNTRY` - For location context in responses
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` - For Telegram mode
- `WAKE_WORD=jarvis` - Voice wake word

## Architecture Overview

### Core Design (Kernel v5.0)

The kernel follows a **semantic routing → execution → enriched response** flow:

1. **SemanticEngine** (Groq) classifies user intent (~200ms)
- Routes to: action, conversation, clarification-needed, tool-specific
- No full LLM call yet

2. **ToolExecutor** executes tools registered in ToolRegistry
- Runs in isolated namespace (sandbox.py)
- Manages working directory context

3. **Response Generation** (NVIDIA full model)
- Enriched with: user context, memory RAG, tool result, conversation history
- Never templates—always prose via LLM

4. **AgentMemory** logs events for cross-session continuity
- FAISS vector index for semantic search
- SQLite for structured queries

### Module Organization

```
core/
├── kernel_impl.py - Main Kernel class, CLI/web/voice/telegram modes
├── llm_gateway.py - NVIDIA/Groq API calls, provider health checks
├── semantic_engine.py - Intent classification and depth analysis
├── tool_registry.py - Tool registration and listing
├── tool_executor.py - Tool execution, sandbox, system commands
├── memory_core.py - Event logging, episodic memory, FAISS search
├── agentic_rag.py - RAG retrieval for context enrichment
├── config_loader.py - Hybrid config extraction (YAML + envvars)
├── goal_alignment_monitor.py- Goal tracking and alignment
└── sandbox.py - Safe execution namespace

autonomy/
├── proactive_engine.py - Background monitoring for nudges
├── habit_profiler.py - User behavior analysis
└── will_engine.py - Intent persistence across sessions

control/
├── accessibility_tree.py - Windows accessibility API integration
├── vision_engine.py - Screenshot + vision model analysis
└── browser_driver.py - Selenium automation

agentic/
├── skill_library.py - Skill registration and execution
├── recipe_engine.py - YAML workflow orchestration
└── subagent_router.py - Multi-agent coordination

evolution/
├── reasoning_engine.py - Chain of Thought, Tree of Thought
├── innovation_engine.py - Domain-specific innovation suggestions
└── metacognition.py - Self-reflection and improvement

interfaces/
├── webui_server.py - FastAPI + WebSocket (live chat, streaming)
├── voice_engine.py - Edge-TTS + PyAudio
├── call_mode.py - Phone mode with call routing
└── jarvis_persona.py - Voice assistant personality

generation/
├── document_reader.py - Multi-format document parsing (PDF, DOCX, CSV)
innovation_engine.py - Idea generation
└── saas_builder.py - Application scaffolding

routing/
└── multi_agent_router.py - Route to specialized agents

safety/
├── guard_protocols.py - Safety checks for tool execution
└── mcp_adapter.py - MCP server integration

workspace/ - Runtime state (SQLite DB, FAISS index, goals, logs)
skills/ - Dynamically loaded Python tools
```

### Key Concepts

**Intent Classification** (SemanticEngine.classify_intent)
- Returns: `{"intent": "action|conversation|clarification", "confidence": 0.0-1.0}`
- Runs on Groq (fast, cheap)

**Tool Execution Model**
- Tools are registered with name, docstring, parameter schema
- Executed in isolated namespace with working directory context
- Sandbox prevents filesystem escape; system commands use explicit allow-list

**Memory System**
- Events logged to SQLite with timestamp, importance score
- FAISS index for semantic similarity search
- Retrieved in response generation context

**Goal Alignment**
- Goals persisted in `workspace/goal_queue.json`
- Proactive engine monitors for opportunities to advance goals
- Self-checks for goal-action alignment

**Workspace Structure**
- `workspace/agent_state.db` - SQLite database for events, history
- `workspace/faiss_index/` - Vector embeddings for semantic search
- `workspace/goal_queue.json` - Pending and active goals
- `workspace/sandbox/` - Isolated execution environment
- `workspace/projects/` - Generated project files
- `workspace/decks/` - Generated presentation decks

## Common Development Tasks

### Adding a New Tool

1. Create function in `core/tool_registry.py` or a module in `skills/`
2. Register via `ToolRegistry.register(name, func, docstring, params_schema)`
3. Test via `run_tests.py` → Tool registry section

```python
from core.tool_registry import ToolRegistry

registry = ToolRegistry()
registry.register(
name="my_tool",
func=my_tool_func,
description="What it does",
params={"param1": {"type": "string"}}
)
```

### Creating a Recipe (YAML Workflow)

Recipes are YAML files in `skills/` that define multi-step workflows:

```yaml
name: "recipe_name"
description: "What this recipe does"
steps:
- tool: "tool_name"
params:
param1: "value"
- tool: "another_tool"
params:
input: "{{previous_step.output}}"
```

### Running a Specific Test

```bash
# Quick test suite method
python -c "from run_tests import *; test_[test_name]()"

# L4 verification method
python -c "from test_l4_verification import *; test_[number]_[name]()"

# Run single test file directly
python test_l4_verification.py
```

### Debugging Mode

Watch the Kernel logs in CLI mode:
```bash
python kernel.py cli
# Logs appear: [Kernel] Intent: "action", [Kernel] Executing: tool_name, etc.
```

Set Python logging level:
```python
import logging
logging.getLogger("Kernel").setLevel(logging.DEBUG)
```

### Adding a New Interface (Web/Voice/Telegram)

1. Add mode handler in `core/kernel_impl.py` → `Kernel.run_[mode]()`
2. Implement in `interfaces/[mode]_server.py`
3. Register in kernel: `elif mode == "custom": self.run_custom()`

### Memory & RAG

To query memory:
```python
from core.memory_core import AgentMemory
memory = AgentMemory("./workspace")
memory.log_event("action", "did something", importance=0.8)
results = memory.semantic_search("similar query", top_k=5)
```

### Safety & Sandboxing

- All tool execution happens in `sandbox.py` namespace
- Filesystem access limited to `WORKSPACE` by default
- Enable via `config: allow_fs_access: true` in tool definition

## Architecture Decisions

### Intent Classification First

**Why**: Avoid expensive full LLM calls for simple router decisions.
- Groq 8B → 200ms, cheap
- NVIDIA 49B → 2+ seconds, expensive
- Classification happens 100% of the time; full LLM only when needed

### NVIDIA for All Prose

**Why**: Router (Groq) for JSON/structured; main model for quality.
- Groq handles intent/routing (fast)
- NVIDIA handles response generation (quality)
- Never mix-and-match responses

### Event-Based Memory

**Why**: Episodic memory (what happened) + state (what I can do) = autonomous continuity.
- Not RAG over documents, but RAG over *experiences*
- Importance scores allow pruning of low-value events
- Works across sessions without retraining

### Sandboxed Tool Execution

**Why**: Safety + context isolation.
- Each tool runs in separate namespace
- No cross-tool state pollution
- Filesystem restricted to workspace

## Performance Tuning

- **Intent classification**: ~200ms (Groq cached)
- **Depth analysis** (if needed): +500ms
- **Tool execution**: Varies (1s-30s+)
- **Response generation**: ~2-5s (NVIDIA streaming)
- **Total turnaround**: 3-8s typical

Cache Groq router calls if user is spamming similar intents.

## Known Limitations & Trade-offs

1. **Tool Execution Sandbox**: Can't execute arbitrary OS commands without explicit registration
2. **Memory Size**: FAISS index grows indefinitely; consider periodic pruning
3. **Concurrency**: Single kernel instance (no multi-agent parallelization yet)
4. **Vision**: Only desktop screenshots (no live camera feed)
5. **Voice**: English-only wake word detection (Porcupine)

## References

- **README.md** - Feature matrix, capability scores, quickstart
- **L4_CAPABILITY_TEST.md** - Validation tests for L4 autonomy
- **SETUP_GUIDE.md** - Detailed Windows setup instructions
- **.env.example** - All configuration options
- **core/kernel_impl.py** - System prompt and Kernel class docstring

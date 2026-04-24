# OpenAGI - Agent Instructions

Use this file for fast, high-signal guidance. Link to canonical docs for details.

## Start Here
Before structural changes (architecture, routing, core systems), read [CLAUDE.md](CLAUDE.md).

Use these docs instead of duplicating details:
- [README.md](README.md): project overview, feature matrix, high-level context
- [SETUP_GUIDE.md](SETUP_GUIDE.md): environment setup and troubleshooting
- [FRONTEND_QUICKSTART.md](FRONTEND_QUICKSTART.md): frontend workflow
- [frontend/README.md](frontend/README.md): frontend app specifics

## Common Commands
### Setup and run
- Setup: setup.bat
- Run: run.bat [mode] or python kernel.py [mode]
- Modes: cli, web (8765), voice, telegram

### Testing
Run the smallest suite that validates your change, then expand if needed:
- Quick core checks: python run_tests.py
- L4 autonomy checks: python test_l4_verification.py
- Extended subsystem coverage: python test_comprehensive.py
- Full L4 + interface sweep: python test_all.py
- Single test function: python -c "from run_tests import *; test_tool_registry()"

## Implementation Conventions
- Keep file operations in workspace/ boundaries and respect sandbox constraints in [core/sandbox.py](core/sandbox.py).
- Register Python tools with ToolRegistry.register() in [core/tool_registry.py](core/tool_registry.py).
- Put multi-step YAML workflows in skills/.
- Tool outcomes are already logged by ToolExecutor; avoid duplicate manual logging unless you need a separate custom event.
- On Python 3.14+, embeddings are disabled by default. Use FORCE_EMBEDDINGS=1 and FORCE_ENCODER=1 only when explicitly required.

## Task-to-File Pointers
- Architecture and routing changes: [CLAUDE.md](CLAUDE.md), [core/kernel_impl.py](core/kernel_impl.py), [core/semantic_engine.py](core/semantic_engine.py)
- Tooling changes: [core/tool_registry.py](core/tool_registry.py), [core/tool_executor.py](core/tool_executor.py), skills/
- Memory behavior: [core/memory_core.py](core/memory_core.py)
- Safety and execution sandbox: [core/sandbox.py](core/sandbox.py)

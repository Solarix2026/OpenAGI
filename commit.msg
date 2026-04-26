feat: OpenAGI v5 Phase 1 - 15 components with 56 passing tests

- config/settings.py: Pydantic v2 settings with .env support, trust zones, memory config
- core/telos_core.py: Immutable value anchor with MappingProxyType, violation protection
- tools/base_tool.py: Tool ABC with typed results via ToolResult dataclass
- memory/memory_core.py: Stratified memory with WORKING, EPISODIC, SEMANTIC, PROCEDURAL layers
- sandbox/repl.py: Subprocess-isolated REPL for code execution with timeout/resourced
- tools/registry.py: Dynamic tool registry with FAISS semantic search, register/invoke
- gateway/llm_gateway.py: LLM router with NVIDIA NIM primary + Groq fallback
- tools/builtin/*.py: 7 built-in tools (shell, file, web, memory, code, etc.)
- skills/skill_loader.py: Markdown skill loader with telos validation
- agents/planner.py: DAG-based planning with cycle detection, topological sort
- agents/executor.py: Parallel execution via asyncio.gather on independent branches
- agents/reflector.py: Post-execution reflection with lesson extraction, memory writes
- core/kernel.py: Main orchestration with AsyncIterator[str] streaming
- api/server.py: FastAPI WebSocket server for streaming execution
- main.py: Entry point starting uvicorn server

Key patterns:
- Zero hardcoded values - all configurable via Settings
- Registry pattern - no hardcoded tool calls
- Proper async/await with asyncio.gather for parallelism
- structlog for structured logging, httpx for HTTP
- Trust zones: TRUSTED/SANDBOXED/ISOLATED execution contexts
- TDD throughout - tests written first, then implementation

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

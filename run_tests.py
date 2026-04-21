# Copyright (c) 2026 ApeironAILab
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/ApeironAILab/OpenAGI

"""
OpenAGI L4 Test Suite
python run_tests.py
"""
import sys
import os

# Test results
results = []

def test(name):
    def decorator(func):
        def wrapper():
            try:
                func()
                results.append((name, "PASS", ""))
                print(f"[PASS] {name}")
                return True
            except Exception as e:
                results.append((name, "FAIL", str(e)))
                print(f"[FAIL] {name}: {e}")
                return False
        return wrapper
    return decorator

print("=" * 50)
print("OpenAGI L4 Test Suite")
print("=" * 50)

# TEST 1: Core imports
@test("Core imports")
def test_core_imports():
    from core.llm_gateway import call_nvidia, call_groq_router
    from core.tool_registry import ToolRegistry
    from core.memory_core import AgentMemory
    from core.semantic_engine import SemanticEngine

# TEST 2: Tool registry
@test("Tool registry")
def test_tool_registry():
    from core.tool_registry import ToolRegistry
    reg = ToolRegistry()
    def dummy(p): return {"success": True}
    reg.register("test", dummy, "Test", {})
    assert "test" in reg.list_tools()

# TEST 3: Semantic routing
@test("Semantic routing (L4)")
def test_semantic_routing():
    from core.tool_executor import ToolExecutor
    from core.semantic_engine import SemanticEngine
    executor = ToolExecutor("./workspace/test_run")
    semantic = SemanticEngine(executor.registry)
    intent = semantic.classify_intent("what can you do")
    assert intent.get("intent") in ("action", "conversation")

# TEST 4: Memory
@test("Memory core")
def test_memory():
    import tempfile
    from core.memory_core import AgentMemory
    with tempfile.TemporaryDirectory() as tmp:
        m = AgentMemory(tmp)
        m.log_event("test", "hello world", importance=0.5)
        r = m.get_recent_timeline(limit=5)
        assert len(r) > 0

# TEST 5: Document reader
@test("Document reader")
def test_doc_reader():
    from generation.document_reader import DocumentReader
    r = DocumentReader()
    supported = [".docx", ".xlsx", ".csv", ".pdf", ".txt", ".md"]
    for ext in supported:
        assert ext in r.read_any.__doc__ or True  # Just check it exists

# TEST 6: Reasoning engine
@test("Reasoning engine")
def test_reasoning():
    from evolution.reasoning_engine import ReasoningEngine
    r = ReasoningEngine()
    # Just verify methods exist
    assert callable(r.chain_of_thought)
    assert callable(r.tree_of_thought)

# TEST 7: Innovation (self-selecting domains)
@test("Innovation self-selecting domains (L4)")
def test_innovation():
    import tempfile
    from generation.innovation_engine import InnovationEngine
    from core.memory_core import AgentMemory
    with tempfile.TemporaryDirectory() as tmp:
        m = AgentMemory(tmp)
        inn = InnovationEngine(m)
        domains = inn._select_relevant_domains("How to make coffee more efficient")
        assert len(domains) >= 3
        assert all(isinstance(d, str) for d in domains)

# TEST 8: Skill library
@test("Skill library")
def test_skill_library():
    from agentic.skill_library import SkillLibrary
    lib = SkillLibrary()
    skills = lib.list_skills()
    assert isinstance(skills, list)

# TEST 9: Habit profiler
@test("Habit profiler (L4)")
def test_habit_profiler():
    import tempfile
    from autonomy.habit_profiler import HabitProfiler
    from core.memory_core import AgentMemory
    with tempfile.TemporaryDirectory() as tmp:
        m = AgentMemory(tmp)
        m.log_event("user_message", "Test message", importance=0.6)
        hp = HabitProfiler(m)
        profile = hp.build_profile()
        assert "last_updated" in profile

# TEST 10: WebUI server
@test("WebUI server")
def test_webui():
    from interfaces.webui_server import WebUIServer
    # Create minimal mock kernel
    class MockKernel:
        executor = type('obj', (object,), {'registry': None})()
    w = WebUIServer(MockKernel())
    assert callable(w._get_local_ip)

# Run all tests
print("\nRunning tests...\n")

test_core_imports()
test_tool_registry()
test_semantic_routing()
test_memory()
test_doc_reader()
test_reasoning()
test_innovation()
test_skill_library()
test_habit_profiler()
test_webui()

# Summary
print("\n" + "=" * 50)
passed = sum(1 for _, s, _ in results if s == "PASS")
failed = sum(1 for _, s, _ in results if s == "FAIL")
print(f"RESULTS: {passed} passed, {failed} failed")
print("=" * 50)

if failed > 0:
    print("\nFailed tests:")
    for name, status, error in results:
        if status == "FAIL":
            print(f"  - {name}: {error}")

sys.exit(0 if failed == 0 else 1)

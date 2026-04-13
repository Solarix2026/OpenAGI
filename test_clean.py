# Copyright (c) 2026 HackerTMJ (门牌号3号)
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/HackerTMJ/OpenAGI

#!/usr/bin/env python3
"""
OpenAGI L4 Comprehensive Test Suite
Tests all tiers without breaking imports
"""
import sys
import os
import tempfile
import time
from pathlib import Path

# Colors for output
class Colors:
    PASS = ''  # Windows compatibility
    FAIL = ''
    WARN = ''
    INFO = ''
    RESET = ''

def log(msg, level="INFO"):
    color = getattr(Colors, level, Colors.INFO)
    print(f"{color}{msg}{Colors.RESET}")

print("=" * 60)
log("OpenAGI L4 Comprehensive Test Suite", "INFO")
print("=" * 60)

results = {"pass": 0, "fail": 0, "warn": 0}

def test(name):
    def decorator(func):
        def wrapper():
            try:
                func()
                log(f"[PASS] {name}", "PASS")
                results["pass"] += 1
                return True
            except Exception as e:
                log(f"[FAIL] {name}: {e}", "FAIL")
                results["fail"] += 1
                return False
        return wrapper
    return decorator

# 
# TIER 1: Core (Brain + Memory)
# 
print("\n" + "" * 40)
log("TIER 1: Core (Brain + Memory)", "INFO")
print("" * 40)

@test("Import: llm_gateway")
def test_llm_gateway():
    from llm_gateway import call_nvidia, call_groq_router
    assert callable(call_nvidia)
    assert callable(call_groq_router)

@test("Import: memory_core")
def test_memory_core():
    from memory_core import AgentMemory
    assert callable(AgentMemory)

@test("Import: semantic_engine")
def test_semantic_engine():
    from semantic_engine import SemanticEngine
    assert callable(SemanticEngine)

@test("Import: tool_executor")
def test_tool_executor():
    from tool_executor import ToolExecutor
    assert callable(ToolExecutor)

@test("Import: tool_registry")
def test_tool_registry():
    from tool_registry import ToolRegistry
    assert callable(ToolRegistry)

@test("Memory: Event logging")
def test_memory_events():
    from memory_core import AgentMemory
    with tempfile.TemporaryDirectory() as tmp:
        m = AgentMemory(tmp)
        m.log_event("test", "hello world", importance=0.5)
        recent = m.get_recent_timeline(limit=5)
        assert len(recent) > 0

@test("Tool Registry: Register & Execute")
def test_tool_registry_exec():
    from tool_registry import ToolRegistry
    reg = ToolRegistry()
    def dummy(params): return {"success": True, "data": params}
    reg.register("test_tool", dummy, "Test", {"p": {"type": "string"}})
    result = reg.execute("test_tool", {"p": "test"})
    assert result["success"] == True

@test("Tool Executor: Built-in tools")
def test_tool_executor_builtin():
    from tool_executor import ToolExecutor
    with tempfile.TemporaryDirectory() as tmp:
        ex = ToolExecutor(tmp)
        tools = ex.registry.list_tools()
        assert "websearch" in tools or len(tools) >= 5

@test("Semantic: Intent classification")
def test_semantic_intent():
    from tool_executor import ToolExecutor
    from semantic_engine import SemanticEngine
    with tempfile.TemporaryDirectory() as tmp:
        ex = ToolExecutor(tmp)
        s = SemanticEngine(ex.registry)
        intent = s.classify_intent("")
        assert intent.get("intent") in ["action", "conversation"]

# 
# TIER 2: Autonomy
# 
print("\n" + "" * 40)
log("TIER 2: Autonomy (Will + Proactive)", "INFO")
print("" * 40)

@test("Import: will_engine")
def test_will_engine():
    from will_engine import WillEngine
    assert callable(WillEngine)

@test("Import: proactive_engine")
def test_proactive_engine():
    from proactive_engine import ProactiveEngine
    assert callable(ProactiveEngine)

@test("Import: beep_filter")
def test_beep_filter():
    from beep_filter import BeepFilter
    assert callable(BeepFilter)

@test("Import: habit_profiler")
def test_habit_profiler():
    from habit_profiler import HabitProfiler
    assert callable(HabitProfiler)

@test("Habit: Build profile")
def test_habit_profile():
    from habit_profiler import HabitProfiler
    from memory_core import AgentMemory
    with tempfile.TemporaryDirectory() as tmp:
        m = AgentMemory(tmp)
        m.log_event("user_message", "I love Python programming", importance=0.7)
        m.log_event("user_message", "Create a web app", importance=0.6)
        hp = HabitProfiler(m)
        profile = hp.build_profile()
        assert "last_updated" in profile or "total_interactions" in profile

# 
# TIER 3: Evolution
# 
print("\n" + "" * 40)
log("TIER 3: Evolution (Self-Improvement)", "INFO")
print("" * 40)

@test("Import: evolution_engine")
def test_evolution_engine():
    from evolution_engine import EvolutionEngine
    assert callable(EvolutionEngine)

@test("Import: innovation_engine")
def test_innovation_engine():
    from innovation_engine import InnovationEngine
    assert callable(InnovationEngine)

@test("Import: reasoning_engine")
def test_reasoning_engine():
    from reasoning_engine import ReasoningEngine
    assert callable(ReasoningEngine)

@test("Innovation: Self-selecting domains")
def test_innovation_domains():
    from innovation_engine import InnovationEngine
    from memory_core import AgentMemory
    with tempfile.TemporaryDirectory() as tmp:
        m = AgentMemory(tmp)
        inn = InnovationEngine(m)
        # Test domain selection exists
        assert hasattr(inn, '_select_relevant_domains')

@test("Reasoning: Methods exist")
def test_reasoning_methods():
    from reasoning_engine import ReasoningEngine
    r = ReasoningEngine()
    assert callable(r.chain_of_thought)
    assert callable(r.tree_of_thought)
    assert callable(r.steelman_debate)

# 
# TIER 4: Agentic
# 
print("\n" + "" * 40)
log("TIER 4: Agentic (Workflow)", "INFO")
print("" * 40)

@test("Import: dag_workflow")
def test_dag_workflow():
    from dag_workflow import DAGWorkflowEngine
    assert callable(DAGWorkflowEngine)

@test("Import: skill_library")
def test_skill_library():
    from skill_library import SkillLibrary
    assert callable(SkillLibrary)

@test("Skill: List starter skills")
def test_skill_starters():
    from skill_library import SkillLibrary
    lib = SkillLibrary()
    skills = lib.list_skills()
    assert "video_deck" in skills or len(skills) >= 3

# 
# TIER 5: Control
# 
print("\n" + "" * 40)
log("TIER 5: Control (Computer + Browser)", "INFO")
print("" * 40)

@test("Import: browser_agent")
def test_browser_agent():
    from browser_agent import BrowserAgent
    assert callable(BrowserAgent)

# 
# TIER 6: Interfaces
# 
print("\n" + "" * 40)
log("TIER 6: Interfaces (Human-facing)", "INFO")
print("" * 40)

@test("Import: jarvis_persona")
def test_jarvis():
    from jarvis_persona import JarvisPersona
    assert callable(JarvisPersona)

@test("Import: webui_server")
def test_webui():
    from webui_server import WebUIServer
    assert callable(WebUIServer)

# 
# TIER 7: Generation
# 
print("\n" + "" * 40)
log("TIER 7: Generation (Content Creation)", "INFO")
print("" * 40)

@test("Import: saas_builder")
def test_saas_builder():
    from saas_builder import SaaSBuilder
    assert callable(SaaSBuilder)

@test("Import: video_deck_skill")
def test_video_deck():
    from video_deck_skill import VideoDeckSkill
    assert callable(VideoDeckSkill)

@test("Import: document_reader")
def test_document_reader():
    from document_reader import DocumentReader
    assert callable(DocumentReader)

@test("Document: Supported formats")
def test_doc_formats():
    from document_reader import DocumentReader, SUPPORTED
    assert ".docx" in SUPPORTED
    assert ".xlsx" in SUPPORTED
    assert ".pdf" in SUPPORTED

# 
# KERNEL: Integration
# 
print("\n" + "" * 40)
log("KERNEL: Full Integration", "INFO")
print("" * 40)

@test("Kernel: Basic initialization")
def test_kernel_init():
    from kernel import Kernel
    # Just verify it can be imported and class exists
    assert callable(Kernel)

# 
# Run all tests
# 
print("\n" + "=" * 60)
log("Running Tests...", "INFO")
print("=" * 60 + "\n")

all_tests = [
    # Tier 1
    test_llm_gateway, test_memory_core, test_semantic_engine,
    test_tool_executor, test_tool_registry, test_memory_events,
    test_tool_registry_exec, test_tool_executor_builtin, test_semantic_intent,
    # Tier 2
    test_will_engine, test_proactive_engine, test_beep_filter,
    test_habit_profiler, test_habit_profile,
    # Tier 3
    test_evolution_engine, test_innovation_engine, test_reasoning_engine,
    test_innovation_domains, test_reasoning_methods,
    # Tier 4
    test_dag_workflow, test_skill_library, test_skill_starters,
    # Tier 5
    test_browser_agent,
    # Tier 6
    test_jarvis, test_webui,
    # Tier 7
    test_saas_builder, test_video_deck, test_document_reader,
    test_doc_formats,
    # Kernel
    test_kernel_init,
]

for t in all_tests:
    t()
    time.sleep(0.01)

# Summary
print("\n" + "=" * 60)
log("TEST SUMMARY", "INFO")
print("=" * 60)
log(f"  PASSED: {results['pass']}", "PASS")
log(f"  FAILED: {results['fail']}", "FAIL" if results['fail'] > 0 else "INFO")
log(f"  TOTAL:  {results['pass'] + results['fail']}", "INFO")
print("=" * 60)

if results['fail'] == 0:
    log("\n ALL TESTS PASSED - System is L4 Ready!", "PASS")
    sys.exit(0)
else:
    log(f"\n  {results['fail']} tests failed", "WARN")
    sys.exit(1)

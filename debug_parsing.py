#!/usr/bin/env python
"""Debug ReAct parsing."""

import asyncio
from gateway.llm_gateway import LLMGateway, LLMMessage
from core.react_loop import ReActLoop
from tools.registry import ToolRegistry
from agents.tool_caller import ToolCallerAgent


async def debug_parsing():
    """Debug ReAct parsing."""
    print("Debugging ReAct parsing...")

    # Initialize components
    gateway = LLMGateway()
    registry = ToolRegistry()
    tool_caller = ToolCallerAgent(registry, gateway)

    # Load builtin tools
    from pathlib import Path
    builtin_path = Path(__file__).parent / "tools" / "builtin"
    if not builtin_path.exists():
        builtin_path = Path(__file__).parent.parent / "tools" / "builtin"
    registered = registry.scan_builtin_directory(builtin_path)

    # Create ReAct loop
    react_loop = ReActLoop(tool_caller, registry, gateway)

    # Test reasoning
    history = [{"role": "user", "content": "what is the current date"}]
    observations = []

    print("\n--- Testing Reasoning ---")
    thought = await react_loop.reason(history, observations)

    print(f"Status: {thought.status}")
    print(f"Reasoning: {thought.reasoning}")
    print(f"Tool: {thought.tool}")
    print(f"Params: {thought.params}")
    print(f"Response: {thought.response}")
    print(f"Is final: {thought.is_final()}")
    print(f"Needs action: {thought.needs_action()}")

    # Test parsing with different formats
    print("\n--- Testing Parsing ---")

    test_cases = [
        "THOUGHT: I need to check the date\nACTION: shell\nPARAMS: {\"command\": \"date\"}",
        "THOUGHT: I can answer now\nFINAL: The date is 2026-04-28",
        "I need to use the shell tool to get the date",
        "FINAL: Here is the answer"
    ]

    for i, test_case in enumerate(test_cases):
        print(f"\nTest case {i+1}: {test_case[:50]}...")
        parsed = react_loop._parse_reasoning(test_case)
        print(f"  Status: {parsed.status}")
        print(f"  Tool: {parsed.tool}")
        print(f"  Response: {parsed.response}")


if __name__ == "__main__":
    asyncio.run(debug_parsing())

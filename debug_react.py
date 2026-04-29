#!/usr/bin/env python
"""Debug ReAct loop reasoning."""

import asyncio
from gateway.llm_gateway import LLMGateway, LLMMessage
from core.react_loop import ReActLoop
from tools.registry import ToolRegistry
from agents.tool_caller import ToolCallerAgent


async def debug_react_reasoning():
    """Debug ReAct reasoning process."""
    print("Debugging ReAct reasoning...")

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
    print(f"Loaded {registered} builtin tools")

    # Create ReAct loop
    react_loop = ReActLoop(tool_caller, registry, gateway)

    # Test reasoning
    history = [{"role": "user", "content": "what is the current date"}]
    observations = []

    print("\nTesting reasoning...")
    thought = await react_loop.reason(history, observations)

    print(f"Thought status: {thought.status}")
    print(f"Thought reasoning: {thought.reasoning}")
    print(f"Thought tool: {thought.tool}")
    print(f"Thought params: {thought.params}")
    print(f"Thought response: {thought.response}")
    print(f"Is final: {thought.is_final()}")
    print(f"Needs action: {thought.needs_action()}")

    # Test the prompt
    print("\n--- Reasoning Prompt ---")
    prompt = react_loop._build_reasoning_prompt(history, observations)
    print(prompt[:500] + "...")


if __name__ == "__main__":
    asyncio.run(debug_react_reasoning())

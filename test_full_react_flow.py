#!/usr/bin/env python
"""Test full ReAct flow with actual components."""

import asyncio
from gateway.llm_gateway import LLMGateway, LLMMessage
from tools.registry import ToolRegistry
from agents.tool_caller import ToolCallerAgent
from core.react_loop import ReActLoop


async def test_full_react_flow():
    """Test the full ReAct flow with actual components."""
    print("Testing full ReAct flow...")

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

    print("\n--- Step 1: Reasoning ---")
    thought = await react_loop.reason(history, observations)

    print(f"Status: {thought.status}")
    print(f"Reasoning: {thought.reasoning}")
    print(f"Tool: {thought.tool}")
    print(f"Params: {thought.params}")
    print(f"Response: {thought.response}")
    print(f"Is final: {thought.is_final()}")
    print(f"Needs action: {thought.needs_action()}")

    if thought.needs_action():
        print("\n--- Step 2: Acting ---")
        observation = await react_loop.act(thought)
        print(f"Observation: {observation}")

        # Add to history and observations
        observations.append(observation)
        history.append({
            "role": "assistant",
            "content": f"Used {thought.tool}: {observation}"
        })

        print("\n--- Step 3: Second reasoning ---")
        thought2 = await react_loop.reason(history, observations)

        print(f"Status: {thought2.status}")
        print(f"Reasoning: {thought2.reasoning}")
        print(f"Tool: {thought2.tool}")
        print(f"Params: {thought2.params}")
        print(f"Response: {thought2.response}")
        print(f"Is final: {thought2.is_final()}")
        print(f"Needs action: {thought2.needs_action()}")

        if thought2.is_final:
            print(f"\n--- Final Response ---")
            print(f"Response: {thought2.response}")


if __name__ == "__main__":
    asyncio.run(test_full_react_flow())

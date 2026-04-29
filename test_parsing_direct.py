#!/usr/bin/env python
"""Test ReAct parsing directly."""

from core.react_loop import ReActLoop, Thought, ThoughtStatus


def test_parsing():
    """Test parsing of LLM response."""
    print("Testing ReAct parsing...")

    # Create a mock ReActLoop
    class MockRegistry:
        def list_tools(self):
            return []

    class MockGateway:
        pass

    class MockToolCaller:
        pass

    react_loop = ReActLoop(MockToolCaller(), MockRegistry(), MockGateway())

    # Test the actual LLM response
    llm_response = """THOUGHT: To find the current date, I can use the shell tool to execute a command that prints the current date.
ACTION: shell
PARAMS: {"command": "date"}"""

    print(f"\n--- Parsing LLM response ---")
    print(f"Response: {llm_response}")

    thought = react_loop._parse_reasoning(llm_response)

    print(f"\n--- Parsed Thought ---")
    print(f"Status: {thought.status}")
    print(f"Reasoning: {thought.reasoning}")
    print(f"Tool: {thought.tool}")
    print(f"Params: {thought.params}")
    print(f"Response: {thought.response}")
    print(f"Is final: {thought.is_final()}")
    print(f"Needs action: {thought.needs_action()}")

    # Test with FINAL response
    final_response = """THOUGHT: I have the information needed
FINAL: The current date is 2026-04-29"""

    print(f"\n--- Parsing FINAL response ---")
    print(f"Response: {final_response}")

    final_thought = react_loop._parse_reasoning(final_response)

    print(f"\n--- Parsed FINAL Thought ---")
    print(f"Status: {final_thought.status}")
    print(f"Reasoning: {final_thought.reasoning}")
    print(f"Tool: {final_thought.tool}")
    print(f"Params: {final_thought.params}")
    print(f"Response: {final_thought.response}")
    print(f"Is final: {final_thought.is_final()}")
    print(f"Needs action: {final_thought.needs_action()}")


if __name__ == "__main__":
    test_parsing()

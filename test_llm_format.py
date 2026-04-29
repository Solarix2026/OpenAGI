#!/usr/bin/env python
"""Test LLM response format for ReAct."""

import asyncio
from gateway.llm_gateway import LLMGateway, LLMMessage


async def test_llm_format():
    """Test if LLM follows ReAct format."""
    print("Testing LLM response format...")

    gateway = LLMGateway()

    # Test the exact prompt used in ReAct loop
    prompt = """You are an AI assistant that uses tools to help users. Think step by step about what to do.

Conversation history:
user: what is the current date

Available tools:
- shell: Execute shell commands
  Parameters: {'command': {'type': 'string', 'description': 'Command to execute'}}

- code: Execute Python code
  Parameters: {'code': {'type': 'string', 'description': 'Python code to execute'}}

- web_search: Search the web
  Parameters: {'query': {'type': 'string', 'description': 'Search query'}}

Think about what you need to do. Respond in this exact format:

If you need to use a tool:
THOUGHT: [your reasoning about what to do next]
ACTION: [tool_name]
PARAMS: {"param": "value"}

If you're ready to respond to the user:
THOUGHT: [your reasoning about the final answer]
FINAL: [your response to the user]

Be concise and direct. Think carefully about whether you need more information or can answer now."""

    print("\n--- Sending prompt to LLM ---")
    print(f"Prompt length: {len(prompt)} chars")

    response = await gateway.complete(
        messages=[LLMMessage(role="user", content=prompt)],
        max_tokens=512,
        temperature=0.0
    )

    print(f"\n--- LLM Response ({len(response.content)} chars) ---")
    print(response.content)
    print("\n--- End of response ---")

    # Try to parse it
    print("\n--- Parsing response ---")
    lines = response.content.strip().split('\n')
    for i, line in enumerate(lines):
        print(f"Line {i}: {repr(line)}")


if __name__ == "__main__":
    asyncio.run(test_llm_format())

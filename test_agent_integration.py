#!/usr/bin/env python
"""Test agent tool invocation integration."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.kernel import Kernel
from core.telos_core import TelosCore


async def test_agent_integration():
    """Test if agent can call tools."""
    print("=" * 60)
    print("AGENT INTEGRATION TEST")
    print("=" * 60)

    # Create kernel
    telos = TelosCore()
    kernel = Kernel(telos=telos)

    # Check integration
    print("\n1. Kernel Status:")
    print(f"   Initialized: {kernel.state.initialized}")
    print(f"   Tools: {len(kernel.registry.list_tools())}")
    print(f"   Skills: {len(kernel.skill_loader.list_skills())}")

    # Test tool invocation
    print("\n2. Testing Tool Invocation:")

    # Test memory tool
    print("   Testing memory tool...")
    result = await kernel.registry.invoke('memory', {
        'action': 'write',
        'content': 'Test agent tool invocation',
        'layer': 'WORKING'
    })
    print(f"   Result: {result.success}")
    if result.success:
        print(f"   Data: {result.data}")
    else:
        print(f"   Error: {result.error}")

    # Test file tool
    print("\n   Testing file tool...")
    result = await kernel.registry.invoke('file', {
        'action': 'read',
        'path': 'README.md'
    })
    print(f"   Result: {result.success}")
    if result.success:
        content = result.data if isinstance(result.data, str) else result.data.get('content', '')
        print(f"   Content length: {len(content)}")
    else:
        print(f"   Error: {result.error}")

    # Test shell tool
    print("\n   Testing shell tool...")
    result = await kernel.registry.invoke('shell', {
        'command': 'echo "Hello from agent"'
    })
    print(f"   Result: {result.success}")
    if result.success:
        output = result.data if isinstance(result.data, str) else result.data.get('output', '')
        print(f"   Output: {output[:50]}...")
    else:
        print(f"   Error: {result.error}")

    # Test tool discovery
    print("\n3. Testing Tool Discovery:")
    tools = kernel.registry.discover('write code', top_k=3)
    print(f"   Found {len(tools)} tools for 'write code':")
    for tool in tools:
        print(f"   - {tool.name}")

    # Test skill invocation
    print("\n4. Testing Skill System:")
    skills = kernel.skill_loader.list_skills()
    print(f"   Available skills: {len(skills)}")
    for skill in skills:
        print(f"   - {skill.name}: {skill.capabilities}")

    print("\n" + "=" * 60)
    print("AGENT INTEGRATION TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_agent_integration())

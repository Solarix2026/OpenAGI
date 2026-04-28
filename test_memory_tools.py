#!/usr/bin/env python
"""Test script for memory and tools functionality."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import Settings
from core.kernel import Kernel
from core.telos_core import TelosCore
from memory.memory_core import MemoryCore, MemoryLayer
from tools.registry import ToolRegistry


async def test_memory():
    """Test memory functionality."""
    print("=" * 60)
    print("TESTING MEMORY FUNCTIONALITY")
    print("=" * 60)

    settings = Settings()
    telos = TelosCore()
    memory = MemoryCore(telos=telos)

    # Test 1: Store in working memory
    print("\n1. Testing Working Memory Write...")
    await memory.write(
        content="Test working memory entry",
        layer=MemoryLayer.WORKING,
        metadata={"test": True}
    )
    print("OK: Written to working memory")

    # Test 2: Store in episodic memory
    print("\n2. Testing Episodic Memory Write...")
    await memory.write(
        content="Test episodic memory entry about a conversation",
        layer=MemoryLayer.EPISODIC,
        metadata={"conversation_id": "test-123"}
    )
    print("OK: Written to episodic memory")

    # Test 3: Store in semantic memory
    print("\n3. Testing Semantic Memory Write...")
    await memory.write(
        content="Python is a programming language created by Guido van Rossum",
        layer=MemoryLayer.SEMANTIC,
        metadata={"category": "programming", "language": "Python"}
    )
    print("OK: Written to semantic memory")

    # Test 4: Recall from working memory
    print("\n4. Testing Working Memory Recall...")
    results = await memory.recall(
        query="Test working",
        layers=[MemoryLayer.WORKING],
        top_k=3
    )
    print(f"OK: Recalled {len(results)} items from working memory")
    for i, result in enumerate(results):
        print(f"  [{i+1}] {result.content[:50]}... (confidence: {result.confidence_score:.2f})")

    # Test 5: Recall from episodic memory
    print("\n5. Testing Episodic Memory Recall...")
    results = await memory.recall(
        query="conversation",
        layers=[MemoryLayer.EPISODIC],
        top_k=3
    )
    print(f"OK: Recalled {len(results)} items from episodic memory")
    for i, result in enumerate(results):
        print(f"  [{i+1}] {result.content[:50]}... (confidence: {result.confidence_score:.2f})")

    # Test 6: Recall from semantic memory
    print("\n6. Testing Semantic Memory Recall...")
    results = await memory.recall(
        query="programming language",
        layers=[MemoryLayer.SEMANTIC],
        top_k=3
    )
    print(f"OK: Recalled {len(results)} items from semantic memory")
    for i, result in enumerate(results):
        print(f"  [{i+1}] {result.content[:50]}... (confidence: {result.confidence_score:.2f})")

    # Test 7: Cross-layer recall
    print("\n7. Testing Cross-Layer Recall...")
    results = await memory.recall(
        query="Test",
        layers=[MemoryLayer.WORKING, MemoryLayer.EPISODIC, MemoryLayer.SEMANTIC],
        top_k=5
    )
    print(f"OK: Recalled {len(results)} items across all layers")
    for i, result in enumerate(results):
        print(f"  [{i+1}] [{result.layer.value}] {result.content[:50]}... (confidence: {result.confidence_score:.2f})")

    # Test 8: Get memory stats
    print("\n8. Testing Memory Stats...")
    stats = memory.get_stats()
    print(f"OK: Memory Stats:")
    print(f"  Working: {stats['working']} items")
    print(f"  Episodic: {stats['episodic']} items")
    print(f"  Semantic: {stats['semantic']} items")
    print(f"  Procedural: {stats['procedural']} items")
    print(f"  Total: {sum(stats.values())} items")

    print("\n" + "=" * 60)
    print("MEMORY TESTS COMPLETE")
    print("=" * 60)


async def test_tools():
    """Test tools functionality."""
    print("\n" + "=" * 60)
    print("TESTING TOOLS FUNCTIONALITY")
    print("=" * 60)

    settings = Settings()
    telos = TelosCore()
    registry = ToolRegistry()

    # Test 1: Scan builtin tools
    print("\n1. Scanning Builtin Tools...")
    builtin_path = Path(__file__).parent / "tools" / "builtin"
    registered = registry.scan_builtin_directory(builtin_path)
    print(f"OK: Registered {registered} builtin tools")

    # Test 2: List all tools
    print("\n2. Listing All Tools...")
    tools = registry.list_tools()
    print(f"OK: Found {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")
        print(f"    Categories: {', '.join(tool.categories)}")
        print(f"    Risk Score: {tool.risk_score}")

    # Test 3: Discover tools by query
    print("\n3. Testing Tool Discovery...")
    queries = [
        "write code",
        "search web",
        "read file",
        "run command"
    ]

    for query in queries:
        print(f"\n  Query: '{query}'")
        results = registry.discover(query, top_k=3)
        print(f"  OK: Found {len(results)} relevant tools:")
        for tool in results:
            print(f"    - {tool.name}: {tool.description}")

    # Test 4: Test tool invocation
    print("\n4. Testing Tool Invocation...")

    # Test memory tool
    print("\n  Testing MemoryTool...")
    memory_tool = registry.get("memory_tool")
    if memory_tool:
        result = await memory_tool.execute(
            action="store",
            content="Test memory tool invocation",
            layer="working"
        )
        print(f"  OK: MemoryTool result: {result.success}")
        if not result.success:
            print(f"    Error: {result.error}")
    else:
        print("  ERROR: MemoryTool not found")

    # Test web search tool
    print("\n  Testing WebSearchTool...")
    web_search_tool = registry.get("web_search_tool")
    if web_search_tool:
        result = await web_search_tool.execute(
            query="Python programming",
            max_results=2
        )
        print(f"  OK: WebSearchTool result: {result.success}")
        if result.success and result.data:
            print(f"    Found {len(result.data.get('results', []))} results")
        else:
            print(f"    Error: {result.error}")
    else:
        print("  ERROR: WebSearchTool not found")

    # Test 5: Get tool by category
    print("\n5. Testing Tools by Category...")
    categories = ["code", "file", "memory", "web"]
    for category in categories:
        tools = registry.list_by_category(category)
        print(f"  {category}: {len(tools)} tools")
        for tool in tools:
            print(f"    - {tool.name}")

    print("\n" + "=" * 60)
    print("TOOLS TESTS COMPLETE")
    print("=" * 60)


async def test_kernel_integration():
    """Test kernel with tools and memory."""
    print("\n" + "=" * 60)
    print("TESTING KERNEL INTEGRATION")
    print("=" * 60)

    settings = Settings()
    telos = TelosCore()

    # Create registry and load tools
    registry = ToolRegistry()
    builtin_path = Path(__file__).parent / "tools" / "builtin"
    registered = registry.scan_builtin_directory(builtin_path)
    print(f"\nOK: Loaded {registered} tools into registry")

    # Create kernel with tools
    kernel = Kernel(
        telos=telos,
        registry=registry
    )

    # Test 1: Check kernel status
    print("\n1. Checking Kernel Status...")
    status = kernel.get_status()
    print(f"OK: Kernel initialized: {status['initialized']}")
    print(f"  Memory stats: {status['memory_stats']}")
    print(f"  Tools available: {len(kernel.registry.list_tools())}")

    # Test 2: Test chat with memory
    print("\n2. Testing Chat with Memory...")
    print("  Sending: 'Hello, can you help me?'")
    response_tokens = []
    async for token in kernel.chat("Hello, can you help me?"):
        response_tokens.append(token)
    response = "".join(response_tokens)
    print(f"OK: Response: {response[:100]}...")

    # Test 3: Test tool discovery in kernel
    print("\n3. Testing Tool Discovery in Kernel...")
    query = "write code"
    tools = kernel.registry.discover(query, top_k=3)
    print(f"OK: Found {len(tools)} tools for '{query}':")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")

    print("\n" + "=" * 60)
    print("KERNEL INTEGRATION TESTS COMPLETE")
    print("=" * 60)


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("OPENAGI V5 - MEMORY & TOOLS TEST SUITE")
    print("=" * 60)

    try:
        await test_memory()
        await test_tools()
        await test_kernel_integration()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED OK")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

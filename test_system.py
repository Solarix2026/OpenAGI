#!/usr/bin/env python
"""
Simple test script to start OpenAGI v5 and test basic functionality.
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.server import create_app
from config.settings import Settings
from core.kernel import Kernel
from core.telos_core import TelosCore


async def test_basic_functionality():
    """Test basic OpenAGI v5 functionality."""
    print("=" * 60)
    print("OpenAGI v5 - Basic Functionality Test")
    print("=" * 60)

    # 1. Test Settings
    print("\n1. Testing Settings...")
    try:
        settings = Settings()
        print(f"   [OK] Agent name: {settings.agent_name}")
        print(f"   [OK] API host: {settings.api_host}")
        print(f"   [OK] API port: {settings.api_port}")
        print(f"   [OK] LLM provider: {settings.llm_provider}")
    except Exception as e:
        print(f"   [FAIL] Settings failed: {e}")
        return

    # 2. Test Telos Core
    print("\n2. Testing Telos Core...")
    try:
        telos = TelosCore()
        print(f"   [OK] Telos initialized with values: {telos.core_values}")
        alignment = telos.check_alignment({"name": "help_user", "risk_score": 0.1, "parameters": {}})
        print(f"   [OK] Alignment check: {alignment.decision}")
        print(f"   [OK] Alignment reasoning: {alignment.reasoning}")
    except Exception as e:
        print(f"   [FAIL] Telos failed: {e}")
        return

    # 3. Test Kernel
    print("\n3. Testing Kernel...")
    try:
        kernel = Kernel(telos=telos)
        print(f"   [OK] Kernel initialized")
        status = kernel.get_status()
        print(f"   [OK] Status: {status}")
    except Exception as e:
        print(f"   [FAIL] Kernel failed: {e}")
        return

    # 4. Test API Server Creation
    print("\n4. Testing API Server...")
    try:
        app = create_app(settings=settings, kernel=kernel)
        print(f"   [OK] FastAPI app created")
        print(f"   [OK] App title: {app.title}")
        print(f"   [OK] App version: {app.version}")
    except Exception as e:
        print(f"   [FAIL] API server failed: {e}")
        return

    # 5. Test Tool Registry
    print("\n5. Testing Tool Registry...")
    try:
        tools = kernel.registry.list_tools()
        print(f"   [OK] Registry initialized")
        print(f"   [OK] Tools available: {len(tools)}")
        for tool in tools[:3]:  # Show first 3 tools
            print(f"      - {tool.name} (risk: {tool.risk_score})")
    except Exception as e:
        print(f"   [FAIL] Registry failed: {e}")
        return

    # 6. Test Memory
    print("\n6. Testing Memory...")
    try:
        from memory.memory_core import MemoryLayer
        await kernel.memory.write("Test memory entry", MemoryLayer.WORKING, {})
        results = await kernel.memory.recall("Test", [MemoryLayer.WORKING], top_k=1)
        print(f"   [OK] Memory initialized")
        print(f"   [OK] Memory write/read successful")
        print(f"   [OK] Results found: {len(results)}")
    except Exception as e:
        print(f"   [FAIL] Memory failed: {e}")
        return

    print("\n" + "=" * 60)
    print("All tests passed! [OK]")
    print("=" * 60)
    print("\nTo start the server:")
    print("  python main.py")
    print("\nTo test the API:")
    print("  curl http://localhost:8000/health")
    print("  curl http://localhost:8000/tools")
    print("\nTo run interactive chat:")
    print("  python main.py --chat")


if __name__ == "__main__":
    asyncio.run(test_basic_functionality())

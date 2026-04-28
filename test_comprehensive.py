#!/usr/bin/env python
"""Comprehensive test of all tool calling and memory functionality."""

import asyncio
import json
import websockets


async def test_comprehensive():
    """Test all tools and memory comprehensively."""
    uri = "ws://localhost:8000/ws"

    print("=" * 60)
    print("COMPREHENSIVE TOOL & MEMORY TEST")
    print("=" * 60)

    try:
        async with websockets.connect(uri) as websocket:
            session_id = "comprehensive-test"

            # Test 1: Code tool (datetime)
            print("\n[1] Testing Code Tool - Get Current Date/Time")
            print("-" * 60)
            await test_message(websocket, "what is the current date and time", session_id)

            # Test 2: Web search tool
            print("\n[2] Testing Web Search Tool")
            print("-" * 60)
            await test_message(websocket, "search for latest AI news 2026", session_id)

            # Test 3: Memory tool - Store information
            print("\n[3] Testing Memory Tool - Store Information")
            print("-" * 60)
            await test_message(websocket, "remember that I prefer Python over JavaScript", session_id)

            # Test 4: Memory tool - Retrieve information
            print("\n[4] Testing Memory Tool - Retrieve Information")
            print("-" * 60)
            await test_message(websocket, "what programming language do I prefer", session_id)

            # Test 5: File tool
            print("\n[5] Testing File Tool - List Files")
            print("-" * 60)
            await test_message(websocket, "list files in the current directory", session_id)

            # Test 6: Shell tool
            print("\n[6] Testing Shell Tool - System Info")
            print("-" * 60)
            await test_message(websocket, "show me the system information", session_id)

            # Test 7: Scraper tool
            print("\n[7] Testing Scraper Tool")
            print("-" * 60)
            await test_message(websocket, "scrape information from https://example.com", session_id)

            # Test 8: Skill tool
            print("\n[8] Testing Skill Tool - List Available Skills")
            print("-" * 60)
            await test_message(websocket, "what skills are available", session_id)

            # Test 9: Complex multi-tool query
            print("\n[9] Testing Complex Multi-Tool Query")
            print("-" * 60)
            await test_message(websocket, "analyze the current project structure and tell me what files are in the tools directory", session_id)

            # Test 10: Memory persistence across sessions
            print("\n[10] Testing Memory Persistence")
            print("-" * 60)
            await test_message(websocket, "what did I tell you about my programming preferences", session_id)

            print("\n" + "=" * 60)
            print("COMPREHENSIVE TEST COMPLETE")
            print("=" * 60)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


async def test_message(websocket, content, session_id):
    """Send a message and get response."""
    message = {
        "type": "message",
        "content": content,
        "session_id": session_id
    }

    await websocket.send(json.dumps(message))

    response = ""
    async for msg in websocket:
        data = json.loads(msg)
        if data["type"] == "token":
            response += data["content"]
        elif data["type"] == "done":
            break
        elif data["type"] == "error":
            print(f"Error: {data['content']}")
            break

    print(f"Response: {response[:300]}{'...' if len(response) > 300 else ''}")

    # Check for tool usage indicators
    if "[Used " in response or "[Analyzing" in response:
        print("[OK] Tool calling detected")
    else:
        print("[WARN] No clear tool usage detected")

    # Check for memory usage
    if "remember" in content.lower() and ("python" in response.lower() or "preference" in response.lower()):
        print("[OK] Memory appears to be working")
    elif "what" in content.lower() and ("python" in response.lower() or "preference" in response.lower()):
        print("[OK] Memory retrieval appears to be working")

    return response


if __name__ == "__main__":
    asyncio.run(test_comprehensive())

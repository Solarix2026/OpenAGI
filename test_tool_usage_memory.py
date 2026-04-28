#!/usr/bin/env python
"""Test if AGI actually uses tools and remembers information."""

import asyncio
import json
import websockets


async def test_tool_usage_and_memory():
    """Test if AGI uses tools and remembers information."""
    uri = "ws://localhost:8000/ws"

    print("=" * 60)
    print("TESTING AGI TOOL USAGE AND MEMORY")
    print("=" * 60)

    try:
        async with websockets.connect(uri) as websocket:
            # Test 1: Ask for current date (should use datetime tool if available)
            print("\nTest 1: Asking for current date")
            print("-" * 60)

            message = {
                "type": "message",
                "content": "what is the date now",
                "session_id": "test-date"
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

            print(f"Response: {response[:200]}...")

            # Test 2: Ask for Meta news (should use web_search tool)
            print("\nTest 2: Asking for Meta news 2026")
            print("-" * 60)

            message = {
                "type": "message",
                "content": "help me find the meta news 2026",
                "session_id": "test-news"
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

            print(f"Response: {response[:300]}...")

            # Test 3: Tell AGI to remember name
            print("\nTest 3: Telling AGI to remember name")
            print("-" * 60)

            message = {
                "type": "message",
                "content": "remember my name is TMJ",
                "session_id": "test-name"
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

            print(f"Response: {response[:200]}...")

            # Test 4: Ask for name (should remember)
            print("\nTest 4: Asking for name (should remember)")
            print("-" * 60)

            message = {
                "type": "message",
                "content": "what is my name",
                "session_id": "test-name-verify"
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

            print(f"Response: {response[:200]}...")

            # Check if name is remembered
            if "TMJ" in response or "tmj" in response.lower():
                print("\n[OK] AGI remembered the name!")
            else:
                print("\n[ERROR] AGI did NOT remember the name")

            print("\n" + "=" * 60)
            print("TEST COMPLETE")
            print("=" * 60)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_tool_usage_and_memory())

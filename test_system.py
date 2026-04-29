#!/usr/bin/env python
"""Simple test script for OpenAGI v5 - run this to test the system."""

import asyncio
import json
import websockets


async def test_system():
    """Test the OpenAGI system with WebSocket."""
    uri = "ws://localhost:8000/ws"

    print("Testing OpenAGI v5 System")
    print("=" * 50)

    try:
        async with websockets.connect(uri) as websocket:
            # Test 1: Simple question
            print("\nTest 1: 'what is the current date'")
            message = {
                "type": "message",
                "content": "what is the current date",
                "session_id": "test-1"
            }

            await websocket.send(json.dumps(message))

            response = ""
            async for msg in websocket:
                data = json.loads(msg)
                content = data.get('content', '')

                if data["type"] == "token":
                    response += content
                    print(f"  Token: {content[:50]}...")
                elif data["type"] == "done":
                    print(f"  Done!")
                    break
                elif data["type"] == "error":
                    print(f"  Error: {content}")
                    break

            print(f"  Full response: {response[:200]}...")

            # Test 2: Web search
            print("\nTest 2: 'search for latest AI news'")
            message = {
                "type": "message",
                "content": "search for latest AI news",
                "session_id": "test-2"
            }

            await websocket.send(json.dumps(message))

            response = ""
            async for msg in websocket:
                data = json.loads(msg)
                content = data.get('content', '')

                if data["type"] == "token":
                    response += content
                    print(f"  Token: {content[:50]}...")
                elif data["type"] == "done":
                    print(f"  Done!")
                    break
                elif data["type"] == "error":
                    print(f"  Error: {content}")
                    break

            print(f"  Full response: {response[:200]}...")

            # Test 3: Code execution
            print("\nTest 3: 'calculate 2+2'")
            message = {
                "type": "message",
                "content": "calculate 2+2",
                "session_id": "test-3"
            }

            await websocket.send(json.dumps(message))

            response = ""
            async for msg in websocket:
                data = json.loads(msg)
                content = data.get('content', '')

                if data["type"] == "token":
                    response += content
                    print(f"  Token: {content[:50]}...")
                elif data["type"] == "done":
                    print(f"  Done!")
                    break
                elif data["type"] == "error":
                    print(f"  Error: {content}")
                    break

            print(f"  Full response: {response[:200]}...")

            print("\n" + "=" * 50)
            print("All tests completed!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Make sure the server is running: python main.py")
    print("Then run this test script.\n")
    asyncio.run(test_system())

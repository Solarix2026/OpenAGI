#!/usr/bin/env python
"""Simple WebSocket test to check server."""

import asyncio
import json
import websockets


async def simple_test():
    """Simple test to check if server is working."""
    uri = "ws://localhost:8000/ws"

    print("Testing server connection...")

    try:
        async with websockets.connect(uri) as websocket:
            message = {
                "type": "message",
                "content": "hello",
                "session_id": "test-simple"
            }

            await websocket.send(json.dumps(message))

            response = ""
            async for msg in websocket:
                data = json.loads(msg)
                print(f"Received: {data['type']}: {data.get('content', '')[:100]}")

                if data["type"] == "token":
                    response += data["content"]
                elif data["type"] == "done":
                    break
                elif data["type"] == "error":
                    print(f"Error: {data['content']}")
                    break

            print(f"\nFull response: {response}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(simple_test())

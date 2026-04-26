#!/usr/bin/env python
"""Test script to verify chat functionality works end-to-end."""
import asyncio
import json
import websockets


async def test_chat():
    """Test the chat WebSocket endpoint."""
    uri = "ws://localhost:8000/ws"

    print("Testing Chat WebSocket...")
    print("=" * 60)

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to OpenAGI v5!")
            print()

            # Send a test message
            test_message = {
                "type": "message",
                "content": "Say 'Hello, World!' in exactly those words.",
                "session_id": "test-session-123"
            }

            print(f"Sending message: {test_message['content']}")
            await websocket.send(json.dumps(test_message))
            print()

            # Stream response
            print("Response: ", end="", flush=True)
            response_text = ""

            async for message in websocket:
                data = json.loads(message)

                if data.get("type") == "token":
                    token = data.get("content", "")
                    print(token, end="", flush=True)
                    response_text += token

                elif data.get("type") == "done":
                    print()
                    print()
                    print("Chat test complete!")
                    print(f"Full response: {response_text}")
                    return True

                elif data.get("type") == "error":
                    print()
                    print(f"Error: {data.get('content', 'Unknown error')}")
                    return False

    except Exception as e:
        print(f"Connection error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_chat())
    exit(0 if success else 1)

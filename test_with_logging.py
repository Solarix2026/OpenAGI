#!/usr/bin/env python
"""Test with detailed logging."""

import asyncio
import json
import websockets


async def test_with_logging():
    """Test with detailed logging."""
    uri = "ws://localhost:8000/ws"

    print("Testing with detailed logging...")

    try:
        async with websockets.connect(uri) as websocket:
            # Test query
            message = {
                "type": "message",
                "content": "what is the current date",
                "session_id": "test-logging"
            }

            print(f"Sending: {message}")
            await websocket.send(json.dumps(message))

            response = ""
            step = 0

            async for msg in websocket:
                data = json.loads(msg)
                content = data.get('content', '')

                print(f"Step {step}: {data['type']} - {content[:100]}")
                step += 1

                if data["type"] == "token":
                    response += content
                elif data["type"] == "done":
                    print("Done signal received")
                    break
                elif data["type"] == "error":
                    print(f"Error: {content}")
                    break

            print(f"\nFull response ({len(response)} chars):\n{response}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_with_logging())

#!/usr/bin/env python
"""Quick test of response generation fix."""

import asyncio
import json
import websockets


async def test_response_generation():
    """Test if response generation is working."""
    uri = "ws://localhost:8000/ws"

    print("Testing response generation fix...")

    try:
        async with websockets.connect(uri) as websocket:
            message = {
                "type": "message",
                "content": "what is the current date",
                "session_id": "test-response-fix"
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

            print(f"Response: {response}")

            # Check if response generation worked
            if "error" in response.lower() and "generating" in response.lower():
                print("[FAIL] Response generation still failing")
            elif "2026" in response or "date" in response.lower():
                print("[SUCCESS] Response generation working!")
            else:
                print("[UNKNOWN] Unclear result")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_response_generation())

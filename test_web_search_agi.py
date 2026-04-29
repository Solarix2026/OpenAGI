#!/usr/bin/env python
"""Test web search through AGI system."""

import asyncio
import json
import websockets


async def test_web_search_agi():
    """Test web search through AGI."""
    uri = "ws://localhost:8000/ws"

    print("Testing web search through AGI...")

    try:
        async with websockets.connect(uri) as websocket:
            message = {
                "type": "message",
                "content": "help me find AI news 2026",
                "session_id": "test-web-search"
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

            # Check if web search worked
            if "AI News" in response or "artificialintelligence-news.com" in response:
                print("[SUCCESS] Web search working!")
            else:
                print("[FAIL] Web search not working properly")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_web_search_agi())

#!/usr/bin/env python
"""Test if AGI correctly lists its tools."""

import asyncio
import json
import websockets
from datetime import datetime


async def test_tool_listing():
    """Test if AGI correctly lists its actual tools."""
    uri = "ws://localhost:8000/ws"

    print("=" * 60)
    print("TESTING AGI TOOL LISTING")
    print("=" * 60)

    try:
        async with websockets.connect(uri) as websocket:
            # Send message asking about tools
            message = {
                "type": "message",
                "content": "what tools do you have",
                "session_id": "test-tool-listing"
            }

            await websocket.send(json.dumps(message))
            print(f"\nSent: {message['content']}")

            # Receive response
            response = ""
            async for message in websocket:
                data = json.loads(message)

                if data["type"] == "token":
                    response += data["content"]
                elif data["type"] == "done":
                    break
                elif data["type"] == "error":
                    print(f"Error: {data['content']}")
                    break

            print(f"\nAGI Response:")
            print("-" * 60)
            print(response)
            print("-" * 60)

            # Check if response contains actual tools
            actual_tools = ["code", "file", "memory", "scraper", "shell", "skill", "web_search"]
            found_tools = [tool for tool in actual_tools if tool in response.lower()]

            print(f"\nActual tools found in response: {len(found_tools)}/7")
            for tool in found_tools:
                print(f"  ✓ {tool}")

            if len(found_tools) >= 5:
                print("\n✅ AGI is correctly listing its tools!")
            else:
                print("\n❌ AGI is NOT correctly listing its tools")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_tool_listing())

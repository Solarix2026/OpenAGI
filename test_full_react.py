#!/usr/bin/env python
"""Test full ReAct loop end-to-end."""

import asyncio
import json
import websockets


async def test_full_react():
    """Test full ReAct loop with tool execution."""
    uri = "ws://localhost:8000/ws"

    print("Testing full ReAct loop...")

    try:
        async with websockets.connect(uri) as websocket:
            # Test query that should trigger ReAct
            message = {
                "type": "message",
                "content": "what is the current date",
                "session_id": "test-full-react"
            }

            await websocket.send(json.dumps(message))

            response = ""
            step_count = 0

            async for msg in websocket:
                data = json.loads(msg)
                content = data.get('content', '')

                if data["type"] == "token":
                    response += content
                    print(f"[Token {step_count}]: {content[:100]}")
                    step_count += 1
                elif data["type"] == "done":
                    print("[Done]")
                    break
                elif data["type"] == "error":
                    print(f"[Error]: {content}")
                    break

            print(f"\nFull response:\n{response}")

            # Check for ReAct indicators
            if "[Thinking:" in response:
                print("\n[OK] ReAct thinking detected")
            if "[Result:" in response:
                print("[OK] ReAct action results detected")
            if "date" in response.lower():
                print("[OK] Date information in response")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_full_react())

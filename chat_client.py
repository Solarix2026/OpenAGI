#!/usr/bin/env python
"""Simple chat client for OpenAGI v5."""
import asyncio
import json
import sys
import websockets
from datetime import datetime


async def chat_client():
    """Interactive chat client for OpenAGI."""
    uri = "ws://localhost:8000/ws"  # Use localhost for client connections

    print("=" * 60)
    print("  OpenAGI v5 - Interactive Chat")
    print("=" * 60)
    print(f"Connecting to: {uri}")
    print("Type 'quit' or 'exit' to stop")
    print()

    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connected to OpenAGI v5!")
            print()

            session_id = f"chat-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

            while True:
                try:
                    # Get user input
                    user_input = input("You: ").strip()

                    if not user_input:
                        continue

                    if user_input.lower() in ['quit', 'exit', 'q']:
                        print("Goodbye!")
                        break

                    # Send message to AGI
                    message = {
                        "type": "message",
                        "content": user_input,
                        "session_id": session_id
                    }

                    await websocket.send(json.dumps(message))

                    # Stream response
                    print("AGI: ", end="", flush=True)
                    response_text = ""

                    async for message in websocket:
                        data = json.loads(message)

                        if data.get("type") == "token":
                            token = data.get("content", "")
                            print(token, end="", flush=True)
                            response_text += token

                        elif data.get("type") == "done":
                            print()  # New line after response
                            break

                        elif data.get("type") == "error":
                            print(f"\nError: {data.get('content', 'Unknown error')}")
                            break

                    print()  # Empty line between messages

                except KeyboardInterrupt:
                    print("\nInterrupted by user")
                    break
                except Exception as e:
                    print(f"\nError: {e}")
                    break

    except Exception as e:
        print(f"Failed to connect: {e}")
        print("Make sure the server is running: python main.py")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(chat_client())
    except KeyboardInterrupt:
        print("\nGoodbye!")

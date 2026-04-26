"""OpenAGI v5 — Entry Point

Main entry point for starting the OpenAGI v5 agent system.

Usage:
    python main.py              # Start API server (default)
    python main.py chat         # Start CLI chat mode
    python main.py web          # Start web interface (future)
    python main.py telegram     # Start Telegram bot (future)
    python main.py check        # Run system health check
"""
import asyncio
import json
import sys
import websockets
from datetime import datetime

import structlog
import uvicorn

from config.settings import get_settings

logger = structlog.get_logger()


def print_banner(mode: str = "server"):
    """Print the OpenAGI banner."""
    config = get_settings()
    agent_name_str = str(config.agent_name)

    print(f"{'='*60}")
    print(f"  {agent_name_str:^56}  ")
    print(f"  Self-Repairing, Tool-Discovering Agent System           ")
    print(f"{'='*60}")

    if mode == "server":
        print(f"  Mode: API Server")
        print(f"  API Server: http://{config.api_host}:{config.api_port}")
        # Show localhost URL for clients
        client_host = "localhost" if config.api_host == "0.0.0.0" else config.api_host
        print(f"  WebSocket:  ws://{client_host}:{config.api_port}/ws")
        print(f"  Health:     http://{config.api_host}:{config.api_port}/health")
    elif mode == "chat":
        print(f"  Mode: CLI Chat")
        client_host = "localhost" if config.api_host == "0.0.0.0" else config.api_host
        print(f"  Connecting to: ws://{client_host}:{config.api_port}/ws")
    elif mode == "check":
        print(f"  Mode: System Health Check")

    print(f"")
    print(f"  Press Ctrl+C to stop")
    print(f"")


def start_server():
    """Start the API server."""
    config = get_settings()
    print_banner("server")

    # Import and create the app
    from api.server import create_app
    app = create_app(settings=config)

    uvicorn.run(
        app,
        host=config.api_host,
        port=config.api_port,
        log_level=config.log_level.lower(),
        reload=False,
    )


async def start_chat():
    """Start CLI chat mode."""
    config = get_settings()
    print_banner("chat")

    # Use localhost for client connections (0.0.0.0 is for server binding only)
    client_host = "localhost" if config.api_host == "0.0.0.0" else config.api_host
    uri = f"ws://{client_host}:{config.api_port}/ws"

    print(f"Connecting to: {uri}")
    print("Type 'quit' or 'exit' to stop")
    print()

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to OpenAGI v5!")
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


def start_web():
    """Start web interface (future)."""
    print_banner("web")
    print("Web interface coming soon!")
    print("For now, use: python main.py chat")
    sys.exit(0)


def start_telegram():
    """Start Telegram bot (future)."""
    print_banner("telegram")
    print("Telegram bot coming soon!")
    print("For now, use: python main.py chat")
    sys.exit(0)


def run_check():
    """Run system health check."""
    print_banner("check")

    print("Running system health check...")
    print()

    try:
        # Test Settings
        print("1. Testing Settings...")
        config = get_settings()
        print(f"   [OK] Agent name: {config.agent_name}")
        print(f"   [OK] API host: {config.api_host}")
        print(f"   [OK] API port: {config.api_port}")
        print(f"   [OK] LLM provider: {config.llm_provider}")
        print()

        # Test Telos Core
        print("2. Testing Telos Core...")
        from core.telos_core import TelosCore
        telos = TelosCore()
        print(f"   [OK] Telos initialized with values: {telos.core_values}")
        alignment = telos.check_alignment({"name": "help_user", "risk_score": 0.1, "parameters": {}})
        print(f"   [OK] Alignment check: {alignment.decision}")
        print(f"   [OK] Alignment reasoning: {alignment.reasoning}")
        print()

        # Test Kernel
        print("3. Testing Kernel...")
        from core.kernel import Kernel
        kernel = Kernel(telos=telos)
        print(f"   [OK] Kernel initialized")
        status = kernel.get_status()
        print(f"   [OK] Status: {status}")
        print()

        # Test API Server Creation
        print("4. Testing API Server...")
        from api.server import create_app
        app = create_app(settings=config, kernel=kernel)
        print(f"   [OK] FastAPI app created")
        print(f"   [OK] App title: {app.title}")
        print(f"   [OK] App version: {app.version}")
        print()

        # Test Tool Registry
        print("5. Testing Tool Registry...")
        tools = kernel.registry.list_tools()
        print(f"   [OK] Registry initialized")
        print(f"   [OK] Tools available: {len(tools)}")
        for tool in tools[:3]:  # Show first 3 tools
            print(f"      - {tool.name} (risk: {tool.risk_score})")
        print()

        # Test Memory
        print("6. Testing Memory...")
        from memory.memory_core import MemoryLayer
        asyncio.run(kernel.memory.write("Test memory entry", MemoryLayer.WORKING, {}))
        results = asyncio.run(kernel.memory.recall("Test", [MemoryLayer.WORKING], top_k=1))
        print(f"   [OK] Memory initialized")
        print(f"   [OK] Memory write/read successful")
        print(f"   [OK] Results found: {len(results)}")
        print()

        print("=" * 60)
        print("All tests passed! [OK]")
        print("=" * 60)
        print()
        print("To start the server:")
        print("  python main.py")
        print()
        print("To start CLI chat:")
        print("  python main.py chat")
        print()
        print("To test the API:")
        print("  curl http://localhost:8000/health")
        print("  curl http://localhost:8000/tools")

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    # Parse command line arguments
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        mode = "server"

    # Route to appropriate mode
    if mode == "server" or mode == "api":
        start_server()
    elif mode == "chat" or mode == "cli":
        asyncio.run(start_chat())
    elif mode == "web":
        start_web()
    elif mode == "telegram" or mode == "tg":
        start_telegram()
    elif mode == "check" or mode == "health":
        run_check()
    else:
        print(f"Unknown mode: {mode}")
        print()
        print("Available modes:")
        print("  python main.py              # Start API server (default)")
        print("  python main.py chat         # Start CLI chat mode")
        print("  python main.py web          # Start web interface (future)")
        print("  python main.py telegram     # Start Telegram bot (future)")
        print("  python main.py check        # Run system health check")
        sys.exit(1)


if __name__ == "__main__":
    main()

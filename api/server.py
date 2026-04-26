# api/server.py
"""FastAPI WebSocket + REST API.

Provides external interface for the agent.
"""
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from config.settings import get_settings
from core.kernel import Kernel
from core.telos_core import TelosCore
from memory.memory_core import MemoryCore
from tools.registry import ToolRegistry

logger = structlog.get_logger()

# Global kernel instance
_kernel: Kernel | None = None
_registry: ToolRegistry | None = None


async def get_kernel() -> Kernel:
    """Get or create kernel instance."""
    global _kernel
    if _kernel is None:
        telos = TelosCore()
        _kernel = Kernel(telos=telos)
    return _kernel


async def get_registry() -> ToolRegistry:
    """Get or create registry instance."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup
    logger.info("api.server.starting")
    await get_kernel()
    await get_registry()
    logger.info("api.server.started")

    yield

    # Shutdown
    logger.info("api.server.shutting_down")
    global _kernel
    if _kernel:
        await _kernel.close()
        _kernel = None
    logger.info("api.server.shutdown")


app = FastAPI(
    title="OpenAGI v5",
    description="Self-Repairing, Tool-Discovering Agent System",
    version="5.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint."""
    return {"status": "healthy", "agent": "OpenAGI-v5"}


@app.get("/status")
async def get_status() -> dict[str, Any]:
    """Get kernel status."""
    kernel = await get_kernel()
    return kernel.get_status()


@app.get("/tools")
async def list_tools() -> list[dict[str, Any]]:
    """List available tools."""
    registry = await get_registry()
    tools = registry.list_tools()
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "risk_score": tool.risk_score,
            "categories": tool.categories,
        }
        for tool in tools
    ]


@app.get("/tools/discover")
async def discover_tools(query: str) -> list[dict[str, Any]]:
    """Discover tools matching query."""
    registry = await get_registry()
    results = registry.discover(query)
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "risk_score": tool.risk_score,
        }
        for tool in results
    ]


@app.get("/memory/stats")
async def memory_stats() -> dict[str, Any]:
    """Get memory statistics."""
    kernel = await get_kernel()
    return kernel.memory.get_stats()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for streaming execution."""
    await websocket.accept()
    kernel = await get_kernel()

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message = data.strip()

            if not message:
                continue

            if message.startswith("/"):
                # Handle commands
                parts = message.split(maxsplit=1)
                command = parts[0]
                args = parts[1] if len(parts) > 1 else ""

                if command == "/run":
                    # Execute goal and stream results
                    async for chunk in kernel.run(args):
                        await websocket.send_text(chunk)
                    await websocket.send_text("[DONE]")

                elif command == "/chat":
                    # Chat and stream response
                    async for chunk in kernel.chat(args):
                        await websocket.send_text(chunk)
                    await websocket.send_text("[DONE]")

                elif command == "/status":
                    status = kernel.get_status()
                    await websocket.send_json({"type": "status", "data": status})

                else:
                    await websocket.send_text(f"Unknown command: {command}")

            else:
                # Default: treat as chat message
                async for chunk in kernel.chat(message):
                    await websocket.send_text(chunk)
                await websocket.send_text("[DONE]")

    except WebSocketDisconnect:
        logger.info("websocket.disconnected")
    except Exception as e:
        logger.exception("websocket.error", error=str(e))
        await websocket.send_text(f"Error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    from config.settings import get_settings

    config = get_settings()
    uvicorn.run(
        "api.server:app",
        host=config.api_host,
        port=config.api_port,
        reload=False,
    )

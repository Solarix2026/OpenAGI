# api/server.py
"""FastAPI server — WebSocket for streaming, REST for health/status.

WebSocket protocol:
  Client → { "type": "message", "content": "...", "session_id": "..." }
  Server → { "type": "token", "content": "..." }  (streaming)
  Server → { "type": "done" }                      (end of response)
  Server → { "type": "error", "content": "..." }   (on error)

REST endpoints:
  GET  /health           → { "status": "ok", "agent": "...", "tools": N }
  GET  /tools            → list of registered tools
  GET  /skills           → list of loaded skills
  POST /memory/recall    → { "query": "...", "layer": "..." } → results
"""
from __future__ import annotations

import json
import uuid
from typing import Optional

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config.settings import Settings
from core.kernel import Kernel

logger = structlog.get_logger()


def create_app(settings: Optional[Settings] = None, kernel: Optional[Kernel] = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="OpenAGI v5", version="5.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Lazy kernel init — created on startup if not injected
    _kernel: dict[str, Kernel] = {}

    @app.on_event("startup")
    async def startup():
        from core.telos_core import TelosCore
        telos = TelosCore()
        k = kernel or Kernel(telos=telos)
        _kernel["instance"] = k
        logger.info("server.startup.complete")

    @app.on_event("shutdown")
    async def shutdown():
        if "instance" in _kernel:
            k = _kernel["instance"]
            if hasattr(k, 'close'):
                await k.close()
        logger.info("server.shutdown")

    @app.get("/health")
    async def health():
        k = _kernel.get("instance")
        return {
            "status": "ok",
            "agent": settings.agent_name,
            "tools": len(k.registry.list_tools()) if k else 0,
        }

    @app.get("/tools")
    async def list_tools():
        k = _kernel.get("instance")
        if not k:
            return {"tools": []}
        return {"tools": [
            {"name": t.name, "description": t.description, "risk": t.risk_score}
            for t in k.registry.list_tools()
        ]}

    @app.get("/skills")
    async def list_skills():
        k = _kernel.get("instance")
        if not k or not hasattr(k, "skill_loader"):
            return {"skills": []}
        return {"skills": [
            {"name": s.name, "capabilities": s.capabilities}
            for s in k.skill_loader.list_skills()
        ]}

    @app.post("/memory/recall")
    async def recall(body: dict):
        k = _kernel.get("instance")
        if not k:
            return {"results": []}
        from memory.memory_core import MemoryLayer
        layer_str = body.get("layer", "working").upper()
        try:
            layer = MemoryLayer[layer_str]
        except KeyError:
            layer = MemoryLayer.WORKING
        items = await k.memory.recall(body.get("query", ""), [layer], top_k=5)
        return {"results": [{"content": i.content, "confidence": i.confidence_score} for i in items]}

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws.accept()
        logger.info("ws.connected", client=ws.client)

        try:
            while True:
                raw = await ws.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await ws.send_json({"type": "error", "content": "Invalid JSON"})
                    continue

                if msg.get("type") != "message":
                    continue

                content = msg.get("content", "").strip()
                if not content:
                    continue

                session_id = msg.get("session_id", f"ws-{uuid.uuid4().hex[:8]}")
                k = _kernel.get("instance")
                if not k:
                    await ws.send_json({"type": "error", "content": "Kernel not ready"})
                    continue

                # Stream tokens
                try:
                    async for token in k.run(content, session_id=session_id):
                        await ws.send_json({"type": "token", "content": token})
                    await ws.send_json({"type": "done"})
                except Exception as e:
                    logger.exception("ws.stream_error", error=str(e))
                    await ws.send_json({"type": "error", "content": str(e)})

        except WebSocketDisconnect:
            logger.info("ws.disconnected", client=ws.client)

    return app

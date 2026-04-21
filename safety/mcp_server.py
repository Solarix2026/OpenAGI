# Copyright (c) 2026 ApeironAILab
# OpenAGI — An Apeiron Product
# MIT License

"""OpenAGI MCP Server — expose OpenAGI tools as MCP protocol."""
import json, logging, os
from pathlib import Path

log = logging.getLogger("MCPServer")

def build_mcp_manifest(tool_registry) -> dict:
    """Convert OpenAGI tool registry to MCP manifest."""
    tools = []
    for name in tool_registry.list_tools():
        spec = tool_registry.get_tool_info(name)
        if not spec:
            continue
        tool_def = {
            "name": name,
            "description": spec.description,
            "inputSchema": {
                "type": "object",
                "properties": {k: {"type": v.get("type", "string"), "description": k} for k, v in (spec.parameters or {}).items()},
                "required": [k for k, v in (spec.parameters or {}).items() if v.get("required")]
            }
        }
        tools.append(tool_def)
    return {"tools": tools}

async def run_mcp_server(kernel, host="127.0.0.1", port=8766):
    """Run MCP server using FastAPI + SSE."""
    from fastapi import FastAPI, Request
    from fastapi.responses import StreamingResponse, JSONResponse
    import uvicorn, asyncio
    app = FastAPI(title="OpenAGI MCP Server")

    @app.get("/")
    async def root():
        return {"name": "openagi", "version": "5.7", "protocol": "mcp"}

    @app.post("/tools/list")
    async def list_tools():
        manifest = build_mcp_manifest(kernel.executor.registry)
        return manifest

    @app.post("/tools/call")
    async def call_tool(request: Request):
        data = await request.json()
        tool_name = data.get("name", "")
        params = data.get("arguments", {})
        if not tool_name:
            return JSONResponse({"error": "No tool name"}, status_code=400)
        try:
            result = kernel.executor.execute({"action": tool_name, "parameters": params})
            return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    # MCP config file for Claude Code
    config_path = Path(".mcp.json")
    mcp_config = {
        "mcpServers": {
            "openagi": {
                "url": f"http://{host}:{port}",
                "description": "OpenAGI tools — computer control, memory, planning, agents"
            }
        }
    }
    config_path.write_text(json.dumps(mcp_config, indent=2))
    log.info("MCP config written to .mcp.json")
    log.info(f"MCP Server: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")

def start_mcp_background(kernel):
    """Start MCP server in background thread."""
    import threading, asyncio
    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_mcp_server(kernel))
    t = threading.Thread(target=_run, daemon=True, name="MCPServer")
    t.start()
    log.info("MCP Server starting on :8766")

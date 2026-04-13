# Copyright (c) 2026 HackerTMJ
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/HackerTMJ/OpenAGI

"""
webui_server_v3.py — Simplified stable Web UI
Focus: Reliability over features
"""
import asyncio
import json
import socket
import os
import logging
from pathlib import Path

log = logging.getLogger("WebUI")

# Simplified HTML - no complex JavaScript
HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>OpenAGI</title>
    <style>
        body { font-family: system-ui, sans-serif; margin: 0; padding: 20px; background: #1a1a2e; color: #eee; }
        #status { padding: 10px; border-radius: 4px; margin-bottom: 20px; }
        .connected { background: #2ecc71; }
        .disconnected { background: #e74c3c; }
        #messages { max-height: 70vh; overflow-y: auto; border: 1px solid #444; padding: 10px; margin-bottom: 10px; }
        .msg { padding: 8px; margin: 5px 0; border-radius: 4px; }
        .user { background: #34495e; margin-left: 20%; }
        .agent { background: #2c3e50; margin-right: 20%; }
        #input-area { display: flex; gap: 10px; }
        #msg-input { flex: 1; padding: 10px; border: none; border-radius: 4px; }
        button { padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #2980b9; }
    </style>
</head>
<body>
    <div id="status" class="disconnected">Connecting...</div>
    <div id="messages"></div>
    <div id="input-area">
        <input type="text" id="msg-input" placeholder="Type message..." />
        <button onclick="sendMessage()">Send</button>
    </div>

<script>
let ws = null;
let reconnectAttempts = 0;

function updateStatus(connected, text) {
    const el = document.getElementById('status');
    el.className = connected ? 'connected' : 'disconnected';
    el.textContent = text;
}

function connect() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(proto + '//' + location.host + '/ws');

    ws.onopen = function() {
        console.log('WebSocket connected');
        updateStatus(true, 'Connected');
        reconnectAttempts = 0;
    };

    ws.onclose = function() {
        console.log('WebSocket closed');
        updateStatus(false, 'Disconnected - reconnecting...');
        ws = null;
        setTimeout(connect, 3000);
    };

    ws.onerror = function(err) {
        console.error('WebSocket error:', err);
        updateStatus(false, 'Error');
    };

    ws.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            console.log('Received:', data);

            if (data.type === 'thinking') {
                addMessage('Thinking...', 'agent');
            } else if (data.type === 'response') {
                removeThinking();
                addMessage(data.text, 'agent');
            } else if (data.type === 'error') {
                removeThinking();
                addMessage('Error: ' + data.text, 'agent');
            }
        } catch (e) {
            console.error('Failed to parse message:', e);
        }
    };
}

function addMessage(text, sender) {
    const msg = document.createElement('div');
    msg.className = 'msg ' + sender;
    msg.textContent = text;
    document.getElementById('messages').appendChild(msg);
    document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;
}

function removeThinking() {
    const msgs = document.getElementById('messages');
    const thinking = msgs.querySelector('.msg.agent:last-child');
    if (thinking && thinking.textContent === 'Thinking...') {
        thinking.remove();
    }
}

function sendMessage() {
    const input = document.getElementById('msg-input');
    const text = input.value.trim();
    if (!text || !ws || ws.readyState !== 1) return;

    addMessage(text, 'user');
    ws.send(JSON.stringify({type: 'message', text: text}));
    input.value = '';
}

// Handle Enter key
document.getElementById('msg-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') sendMessage();
});

// Start connection when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', connect);
} else {
    connect();
}
</script>
</body>
</html>
"""


class WebUIServer:
    def __init__(self, kernel):
        self.kernel = kernel
        self._active_ws = set()

    def _get_local_ip(self) -> str:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
        finally:
            s.close()

    async def _push_to_all(self, message: str):
        """Push message to all connected WebSocket clients."""
        if not self._active_ws:
            return
        dead = set()
        for ws in self._active_ws:
            try:
                await ws.send_json({"type": "proactive", "text": message})
            except Exception:
                dead.add(ws)
        self._active_ws -= dead

    def push_sync(self, message: str):
        """Sync-safe push called from background threads."""
        if not self._active_ws:
            return
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self._push_to_all(message), loop)
        except Exception as e:
            log.debug(f"Push failed: {e}")

    def start(self, host="0.0.0.0", port=None):
        from fastapi import FastAPI, WebSocket, WebSocketDisconnect
        from fastapi.responses import HTMLResponse
        import uvicorn

        port = port or int(os.getenv("WEBUI_PORT", "8765"))
        app = FastAPI()

        # Wire push function
        if self.kernel:
            self.kernel._webui_push = self.push_sync

        @app.get("/", response_class=HTMLResponse)
        async def index():
            return HTML

        @app.get("/health")
        async def health():
            return {"status": "ok", "connections": len(self._active_ws)}

        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self._active_ws.add(websocket)
            log.info(f"Client connected, total: {len(self._active_ws)}")

            try:
                while True:
                    raw = await websocket.receive_text()
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        await websocket.send_json({"type": "error", "text": "Invalid JSON"})
                        continue

                    if data.get("type") != "message":
                        continue

                    text = data.get("text", "").strip()
                    if not text:
                        continue

                    # Send thinking indicator
                    await websocket.send_json({"type": "thinking"})

                    # Process in thread pool to not block
                    loop = asyncio.get_event_loop()
                    try:
                        response = await loop.run_in_executor(
                            None, self.kernel.process, text
                        )
                        await websocket.send_json({"type": "response", "text": response})
                    except Exception as e:
                        log.error(f"Process error: {e}")
                        await websocket.send_json({"type": "error", "text": str(e)})

            except WebSocketDisconnect:
                log.info("Client disconnected")
            except Exception as e:
                log.error(f"WebSocket error: {e}")
            finally:
                self._active_ws.discard(websocket)

        ip = self._get_local_ip()
        url = f"http://{ip}:{port}"
        log.info(f"Web UI starting on {url}")

        # Generate QR
        try:
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=2, border=1)
            qr.add_data(url)
            qr.make(fit=True)
            qr.print_ascii(invert=True)
        except Exception:
            pass

        print(f"\nOpen: {url}\n")

        uvicorn.run(app, host=host, port=port, log_level="warning")

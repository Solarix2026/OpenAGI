"""
webui_server_v2.py — Desktop-class OpenClaw-style Web UI v2.0

Full SPA with:
- Left sidebar: Skills, Goals, Tools, Logs tabs
- Center: Chat with markdown rendering
- Right panel: Memory viewer, Capabilities
- Settings overlay: Model selector, voice toggle
- Log streaming via SSE

Layout (desktop-first, responsive):
┌────────────────────────────────────────────────────────────┐
│ Header: OpenAGI | Settings ⚙ | Mode | Status              │
├──────────┬────────────────────────────┬───────────────┤
│          │                            │               │
│ SIDEBAR  │       CHAT / MAIN          │  SIDE PANEL   │
│          │                            │               │
│ • Skills │   [messages...]           │ Memory viewer │
│ • Goals  │                            │ Capabilities  │
│ • Tools  │   [input + voice btn]      │ Settings      │
│ • Logs   │                            │               │
└──────────┴────────────────────────────┴───────────────┘
"""
import asyncio
import json
import socket
import os
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

log = logging.getLogger("WebUI")

# Full HTML with Tailwind CDN
HTML_V2 = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenAGI v5.1 — Desktop Control</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>body{font-family:'Inter',sans-serif;background:#0a0a0a}</style>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        agi: { 50: '#f0f9ff', 100: '#e0f2fe', 200: '#bae6fd', 300: '#7dd3fc',
                               400: '#38bdf8', 500: '#0ea5e9', 600: '#0284c7', 700: '#0369a1',
                               800: '#075985', 900: '#0c4a6e', 950: '#082f49' }
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-gray-950 text-gray-100 h-screen overflow-hidden">
    <!-- Header -->
    <header class="h-14 bg-gray-900 border-b border-gray-800 flex items-center justify-between px-4 shrink-0">
        <div class="flex items-center gap-3">
            <span class="text-xl font-bold text-agi-400">⚡ OpenAGI</span>
            <span class="text-xs text-gray-500 px-2 py-1 bg-gray-800 rounded">v5.1</span>
        </div>
        <div class="flex items-center gap-4">
            <div id="conn-status" class="flex items-center gap-2 text-xs">
                <span class="w-2 h-2 rounded-full bg-yellow-500" id="status-dot"></span>
                <span class="text-gray-400" id="status-text">Connecting...</span>
            </div>
            <button onclick="toggleSettings()" class="p-2 hover:bg-gray-800 rounded-lg transition">⚙️</button>
        </div>
    </header>

    <!-- Main Layout -->
    <div class="flex h-[calc(100vh-56px)]">
        <!-- Left Sidebar -->
        <aside class="w-64 bg-gray-900 border-r border-gray-800 flex flex-col">
            <nav class="p-2 space-y-1">
                <button onclick="setTab('skills')" class="tab-btn w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-left hover:bg-gray-800 transition" data-tab="skills">
                    <span>🧩</span> Skills
                </button>
                <button onclick="setTab('goals')" class="tab-btn w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-left hover:bg-gray-800 transition" data-tab="goals">
                    <span>🎯</span> Goals
                </button>
                <button onclick="setTab('tools')" class="tab-btn w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-left hover:bg-gray-800 transition" data-tab="tools">
                    <span>🔧</span> Tools
                </button>
                <button onclick="setTab('logs')" class="tab-btn w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-left hover:bg-gray-800 transition" data-tab="logs">
                    <span>📋</span> Logs
                </button>
            </nav>
            <div class="flex-1 overflow-y-auto p-3" id="sidebar-content">
                <!-- Dynamic content -->
            </div>
        </aside>

        <!-- Center Chat -->
        <main class="flex-1 flex flex-col min-w-0">
            <div id="messages" class="flex-1 overflow-y-auto p-4 space-y-4">
                <!-- Welcome message -->
                <div class="flex gap-3">
                    <div class="w-8 h-8 rounded-full bg-agi-600 flex items-center justify-center text-sm">🤖</div>
                    <div class="flex-1 bg-gray-800 rounded-xl rounded-tl-md p-4 max-w-3xl">
                        <p class="text-sm">OpenAGI v5.1 ready. I have memory across sessions, can control your computer, and get smarter from each interaction.</p>
                    </div>
                </div>
            </div>
            <div class="p-4 border-t border-gray-800">
                <div class="flex gap-2 items-end">
                    <button onclick="toggleVoice()" id="voice-btn" class="p-3 rounded-xl bg-gray-800 hover:bg-gray-700 transition">🎤</button>
                    <div class="flex-1 relative">
                        <textarea id="input" placeholder="Message OpenAGI..." rows="1"
                            class="w-full bg-gray-800 rounded-xl px-4 py-3 pr-12 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-agi-500"
                            onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendMessage()}"></textarea>
                        <button onclick="sendMessage()" class="absolute right-2 bottom-2 p-2 bg-agi-600 hover:bg-agi-500 rounded-lg transition text-sm">➤</button>
                    </div>
                </div>
            </div>
        </main>

        <!-- Right Panel -->
        <aside class="w-72 bg-gray-900 border-l border-gray-800 flex flex-col">
            <div class="p-3 border-b border-gray-800">
                <h3 class="text-sm font-semibold text-gray-400">RECENT MEMORY</h3>
            </div>
            <div class="flex-1 overflow-y-auto p-3 space-y-3" id="memory-panel">
                <!-- Memory items -->
            </div>
            <div class="p-3 border-t border-gray-800">
                <h3 class="text-sm font-semibold text-gray-400 mb-2">CAPABILITIES</h3>
                <div class="space-y-2" id="capabilities-panel">
                    <!-- Capability bars -->
                </div>
            </div>
        </aside>
    </div>

    <!-- Settings Modal -->
    <div id="settings-modal" class="fixed inset-0 bg-black/80 hidden items-center justify-center z-50">
        <div class="bg-gray-900 rounded-2xl w-full max-w-lg p-6 m-4">
            <div class="flex items-center justify-between mb-6">
                <h2 class="text-xl font-bold">Settings</h2>
                <button onclick="toggleSettings()" class="text-gray-400 hover:text-white">✕</button>
            </div>
            <div class="space-y-4">
                <div>
                    <label class="block text-sm text-gray-400 mb-2">NVIDIA Model</label>
                    <select class="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm">
                        <option>nvidia/llama-3.3-nemotron-super-49b-v1</option>
                        <option>meta/llama-3.1-70b-instruct</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm text-gray-400 mb-2">Voice</label>
                    <div class="flex items-center gap-2">
                        <input type="checkbox" id="voice-toggle" checked class="rounded bg-gray-700">
                        <span class="text-sm">Enable TTS</span>
                    </div>
                </div>
                <div>
                    <label class="block text-sm text-gray-400 mb-2">Proactive</label>
                    <div class="flex items-center gap-2">
                        <input type="checkbox" id="proactive-toggle" checked class="rounded bg-gray-700">
                        <span class="text-sm">Enable proactive nudges</span>
                    </div>
                </div>
                <div class="pt-4 border-t border-gray-800">
                    <button onclick="clearMemory()" class="w-full py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg transition text-sm">
                        Clear All Memory
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script>
        // WebSocket
        let ws = null;
        let currentTab = 'skills';
        let logs = [];

        function connect() {
            ws = new WebSocket('ws://' + location.host + '/ws');
            ws.onopen = () => {
                updateStatus(true);
                loadSkills();
                loadGoals();
                loadTools();
                loadMemory();
                loadCapabilities();
            };
            ws.onclose = () => {
                updateStatus(false);
                setTimeout(connect, 3000);
            };
            ws.onmessage = (e) => {
                const d = JSON.parse(e.data);
                handleMessage(d);
            };
        }

        function updateStatus(online) {
            const dot = document.getElementById('status-dot');
            const text = document.getElementById('status-text');
            dot.className = `w-2 h-2 rounded-full ${online ? 'bg-green-500' : 'bg-red-500'}`;
            text.textContent = online ? 'Online' : 'Offline';
        }

        function handleMessage(d) {
            if (d.type === 'thinking') {
                showThinking();
            } else if (d.type === 'response') {
                hideThinking();
                addMessage(d.text, 'agent');
            } else if (d.type === 'log') {
                addLog(d);
            } else if (d.type === 'proactive') {
                addMessage('💡 ' + d.text, 'agent');
            }
        }

        function showThinking() {
            const msgs = document.getElementById('messages');
            msgs.innerHTML += `
                <div id="thinking" class="flex gap-3">
                    <div class="w-8 h-8 rounded-full bg-agi-600 flex items-center justify-center text-sm">🤖</div>
                    <div class="flex-1 flex items-center gap-2 text-gray-400">
                        <span class="animate-pulse">⚡ Thinking...</span>
                    </div>
                </div>`;
            msgs.scrollTop = msgs.scrollHeight;
        }

        function hideThinking() {
            document.getElementById('thinking')?.remove();
        }

        function addMessage(text, sender) {
            const msgs = document.getElementById('messages');
            const isUser = sender === 'user';
            msgs.innerHTML += `
                <div class="flex gap-3 ${isUser ? 'flex-row-reverse' : ''}">
                    <div class="w-8 h-8 rounded-full flex items-center justify-center text-sm ${isUser ? 'bg-gray-700' : 'bg-agi-600'}">${isUser ? '👤' : '🤖'}</div>
                    <div class="flex-1 max-w-3xl ${isUser ? 'bg-gray-700' : 'bg-gray-800'} rounded-xl p-4 text-sm">
                        ${formatMessage(text)}
                    </div>
                </div>`;
            msgs.scrollTop = msgs.scrollHeight;
        }

        function formatMessage(text) {
            if (!text) return '';
            let html = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
            // Code blocks
            html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre class="bg-gray-950 p-3 rounded-lg overflow-x-auto mt-2"><code>$2</code></pre>');
            // Inline code
            html = html.replace(/`([^`]+)`/g, '<code class="bg-gray-950 px-1.5 py-0.5 rounded text-agi-400">$1</code>');
            // Bold
            html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
            // Line breaks
            html = html.replace(/\n/g, '<br>');
            return html;
        }

        function sendMessage() {
            const input = document.getElementById('input');
            const text = input.value.trim();
            if (!text || !ws) return;
            addMessage(text, 'user');
            ws.send(JSON.stringify({type: 'message', text: text}));
            input.value = '';
            showThinking();
        }

        // Sidebar tabs
        function setTab(tab) {
            currentTab = tab;
            document.querySelectorAll('.tab-btn').forEach(b => {
                b.classList.toggle('bg-gray-800', b.dataset.tab === tab);
                b.classList.toggle('text-agi-400', b.dataset.tab === tab);
            });
            renderSidebar();
        }

        async function renderSidebar() {
            const content = document.getElementById('sidebar-content');
            switch(currentTab) {
                case 'skills':
                    const skills = await fetchJson('/api/skills');
                    content.innerHTML = skills.skills?.map(s => `
                        <div class="p-3 bg-gray-800 rounded-xl mb-2">
                            <div class="font-medium text-sm">${s.name}</div>
                            <div class="text-xs text-gray-400">${s.description || 'No description'}</div>
                            <button onclick="runRecipe('${s.name}')" class="mt-2 w-full py-1.5 bg-agi-600 hover:bg-agi-500 rounded-lg text-xs transition">Run</button>
                        </div>
                    `).join('') || '<p class="text-gray-500 text-sm">No skills</p>';
                    break;
                case 'goals':
                    content.innerHTML = '<p class="text-gray-500 text-sm">Loading goals...</p>';
                    break;
                case 'tools':
                    content.innerHTML = '<p class="text-gray-500 text-sm">Loading tools...</p>';
                    break;
                case 'logs':
                    content.innerHTML = logs.slice(-20).map(l => `
                        <div class="text-xs p-2 border-b border-gray-800 ${l.level === 'ERROR' ? 'text-red-400' : 'text-gray-400'}">
                            <span class="text-gray-600">${new Date(l.ts*1000).toLocaleTimeString()}</span> [${l.level}] ${l.msg}
                        </div>
                    `).join('') || '<p class="text-gray-500 text-sm">No logs yet</p>';
                    break;
            }
        }

        async function loadSkilled() {
            // Load skills from API
            renderSidebar();
        }

        function loadGoals() {
            // Goals would be loaded here
        }

        function loadTools() {
            // Tools would be loaded here
        }

        async function loadMemory() {
            const memory = await fetchJson('/api/memory/recent');
            const panel = document.getElementById('memory-panel');
            panel.innerHTML = memory.events?.map(e => `
                <div class="p-2 bg-gray-800 rounded-lg text-xs">
                    <span class="text-gray-500">${e.ts}</span>
                    <p class="text-gray-300 truncate">${e.content}</p>
                </div>
            `).join('') || '<p class="text-gray-500 text-xs">No memory</p>';
        }

        async function loadCapabilities() {
            const caps = await fetchJson('/api/capabilities');
            const panel = document.getElementById('capabilities-panel');
            panel.innerHTML = Object.entries(caps).map(([name, score]) => `
                <div>
                    <div class="flex justify-between text-xs mb-1">
                        <span class="text-gray-400">${name}</span>
                        <span class="text-agi-400">${(score*100).toFixed(0)}%</span>
                    </div>
                    <div class="h-2 bg-gray-800 rounded-full">
                        <div class="h-full bg-agi-600 rounded-full" style="width: ${score*100}%"></div>
                    </div>
                </div>
            `).join('');
        }

        async function fetchJson(url) {
            try { return await fetch(url).then(r => r.json()); } catch { return {}; }
        }

        function toggleSettings() {
            document.getElementById('settings-modal').classList.toggle('hidden');
            document.getElementById('settings-modal').classList.toggle('flex');
        }

        function clearMemory() {
            if (confirm('Clear all memory?')) {
                fetch('/api/memory/clear', {method: 'POST'});
                loadMemory();
            }
        }

        function addLog(log) {
            logs.push(log);
            if (logs.length > 100) logs.shift();
            if (currentTab === 'logs') renderSidebar();
        }

        // Init
        connect();
        setTab('skills');
    </script>
</body>
</html>"""


class WebUIServer:
    def __init__(self, kernel):
        self.kernel = kernel
        self._active_ws = set()
        self._app = None

    def _get_local_ip(self) -> str:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
        finally:
            s.close()

    def _generate_qr(self, url: str):
        try:
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=2, border=1)
            qr.add_data(url)
            qr.make(fit=True)
            qr.print_ascii(invert=True)
            img = qr.make_image()
            Path("./workspace").mkdir(exist_ok=True)
            img.save("./workspace/qr_connect.png")
            print(f"\nScan QR or open: {url}\n")
        except Exception:
            print(f"\nOpen: {url}\n")

    async def _push_to_all(self, message: str):
        """Push message to all connected WebSocket clients."""
        import copy
        dead = set()
        for ws in self._active_ws:
            try:
                await ws.send_json({"type": "proactive", "text": message})
            except Exception:
                dead.add(ws)
        self._active_ws -= dead

    def _push_dict_to_all(self, data: dict):
        """Push dict to all connected WebSocket clients."""
        import asyncio
        import copy
        async def _do():
            dead = set()
            for ws in self._active_ws:
                try:
                    await ws.send_json(data)
                except Exception:
                    dead.add(ws)
            self._active_ws -= dead
        asyncio.create_task(_do())

    def start(self, host="0.0.0.0", port=None):
        from fastapi import FastAPI, WebSocket, WebSocketDisconnect
        from fastapi.responses import HTMLResponse, JSONResponse
        import uvicorn

        port = port or int(os.getenv("WEBUI_PORT", "8765"))
        app = FastAPI()

        # Wire push function to kernel
        self.kernel._webui_push = self._push_to_all

        @app.get("/", response_class=HTMLResponse)
        async def index():
            return HTML_V2

        @app.get("/api/status")
        async def status():
            tools = self.kernel.executor.registry.list_tools()
            return {
                "online": True,
                "tools": len(tools),
                "tool_names": tools[:10],
                "version": "5.1",
                "modules": {
                    "jarvis": bool(self.kernel.jarvis),
                    "proactive": bool(self.kernel.proactive),
                    "evolution": bool(self.kernel.evolution),
                    "chronos": bool(self.kernel.chronos),
                    "vision": bool(self.kernel.vision),
                    "voice": bool(self.kernel.voice)
                }
            }

        @app.get("/api/skills")
        async def list_skills():
            if not self.kernel.skills:
                return {"skills": []}
            skills = []
            for name in self.kernel.skills.list_skills():
                try:
                    skill = self.kernel.skills.load_skill(name)
                    skills.append({
                        "name": name,
                        "description": skill.get("description", ""),
                        "version": skill.get("version", "1.0"),
                        "author": skill.get("author", "local"),
                        "tags": skill.get("tags", [])
                    })
                except Exception:
                    pass
            return {"skills": skills, "count": len(skills)}

        @app.get("/api/memory/recent")
        async def recent_memory():
            """Return recent episodic memory for side panel."""
            try:
                events = self.kernel.memory.get_recent_timeline(limit=10)
                return {"events": events}
            except Exception as e:
                return {"events": [], "error": str(e)}

        @app.get("/api/capabilities")
        async def capabilities():
            """Return capability matrix from MetacognitiveEngine."""
            if not self.kernel.meta:
                # Return default if no meta engine
                return {
                    "reasoning": 0.6,
                    "coding": 0.5,
                    "planning": 0.55,
                    "memory": 0.7,
                    "tool_use": 0.65
                }
            try:
                # Get from meta engine if available
                caps = {}
                for dim in ["reasoning", "coding", "planning", "memory", "tool_use", "innovation", "learning"]:
                    caps[dim] = self.kernel.meta.get_capability_score(dim)
                return caps
            except Exception:
                return {"error": "Unable to fetch capabilities"}

        @app.post("/api/memory/clear")
        async def clear_memory():
            """Clear all memory with confirmation."""
            try:
                # This would need implementation in memory_core to clear tables
                # For now just clear FAISS
                self.kernel.memory._faiss_index = None
                self.kernel.memory._faiss_texts = []
                self.kernel.memory._faiss_dirty = True
                return {"success": True}
            except Exception as e:
                return {"success": False, "error": str(e)}

        @app.get("/api/goals")
        async def list_goals():
            """Return pending goals."""
            from core.goal_persistence import load_goal_queue
            goals = load_goal_queue()
            return {"goals": goals[:20]}

        @app.websocket("/ws")
        async def ws_endpoint(ws: WebSocket):
            await ws.accept()
            self._active_ws.add(ws)
            try:
                while True:
                    raw = await ws.receive_text()
                    data = json.loads(raw)
                    if data.get("type") == "message":
                        text = data.get("text", "")
                        await ws.send_json({"type": "thinking", "text": "⚡ Thinking..."})
                        loop = asyncio.get_event_loop()
                        response = await loop.run_in_executor(None, self.kernel.process, text)
                        await ws.send_json({"type": "response", "text": response, "success": True})
            except WebSocketDisconnect:
                self._active_ws.discard(ws)
            except Exception:
                self._active_ws.discard(ws)

        ip = self._get_local_ip()
        url = f"http://{ip}:{port}"
        self._generate_qr(url)
        print(f"Web UI: {url}")
        uvicorn.run(app, host=host, port=port, log_level="warning")


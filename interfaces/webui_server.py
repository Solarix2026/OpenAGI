"""
webui_server.py — Web UI and phone bridge

python kernel.py web → starts server → prints QR code to terminal
Phone scans QR → opens mobile chat UI → full kernel access via WebSocket

Architecture:
- FastAPI on 0.0.0.0:8765
- GET / → dark mobile chat HTML (inline, no external files needed)
- POST /api/chat → kernel.process(message)
- GET /api/status → system status
- GET /api/skills → list installed skills
- POST /api/skills/run → execute skill
- POST /api/skills/install → install from URL
- WS /ws → real-time bidirectional (phone bridge)
- GET /qr → QR code PNG

WebSocket protocol:
- Client → {"type":"message","text":"..."}
- Server → {"type":"thinking","text":"⚡ Processing..."}
- Server → {"type":"response","text":"...","success":true}
- Server → {"type":"proactive","text":"..."} (pushed from proactive engine)
"""
import asyncio
import json
import socket
import os
import logging
from pathlib import Path

log = logging.getLogger("WebUI")

# HTML inline — complete mobile-first dark UI with Skills modal
HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>OpenAGI</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,system-ui,sans-serif;background:#0a0a0a;color:#e8e8e8;height:100vh;display:flex;flex-direction:column;overflow:hidden}
#header{background:#111;padding:12px 16px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #222;flex-shrink:0}
#header h1{font-size:18px;font-weight:600;color:#4fc3f7;letter-spacing:-0.5px}
#status{font-size:11px;color:#666;display:flex;align-items:center;gap:4px}
#status::before{content:'';width:6px;height:6px;border-radius:50%;background:#666;display:inline-block}
#status.connected::before{background:#2ecc71}
#messages{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px;-webkit-overflow-scrolling:touch}
.msg{max-width:85%;padding:10px 14px;border-radius:16px;font-size:15px;line-height:1.5;word-break:break-word;white-space:pre-wrap}
.user{align-self:flex-end;background:#1a6fb5;color:#fff;border-radius:16px 16px 4px 16px}
.agent{align-self:flex-start;background:#1e1e1e;color:#e8e8e8;border-radius:4px 16px 16px 16px;border:1px solid #2a2a2a}
.thinking{align-self:flex-start;color:#555;font-style:italic;font-size:13px}
#quickbtns{display:flex;gap:8px;padding:8px 12px;overflow-x:auto;background:#0f0f0f;border-top:1px solid #1a1a1a;flex-shrink:0;scrollbar-width:none}
#quickbtns::-webkit-scrollbar{display:none}
.qbtn{background:#1a1a1a;border:1px solid #2a2a2a;color:#aaa;padding:6px 14px;border-radius:20px;font-size:12px;white-space:nowrap;cursor:pointer;flex-shrink:0;-webkit-tap-highlight-color:transparent}
.qbtn:active{background:#2a2a2a;color:#fff}
#inputbar{display:flex;gap:8px;padding:10px 12px;background:#111;border-top:1px solid #1a1a1a;flex-shrink:0}
#input{flex:1;background:#1a1a1a;border:1px solid #2a2a2a;color:#e8e8e8;padding:10px 14px;border-radius:24px;font-size:15px;outline:none;resize:none;max-height:80px}
#input:focus{border-color:#4fc3f7}
#sendbtn,#voicebtn{background:#1a6fb5;border:none;color:#fff;width:42px;height:42px;border-radius:50%;font-size:16px;cursor:pointer;flex-shrink:0;-webkit-tap-highlight-color:transparent}
#voicebtn{background:#1a1a1a;border:1px solid #333;color:#aaa}
#voicebtn.listening{background:#c0392b;border-color:#e74c3c;color:#fff;animation:pulse 1s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.6}}
/* Skills Modal */
#skills-modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.92);z-index:100;flex-direction:column}
#skills-modal.open{display:flex}
#skills-header{background:#111;padding:14px 16px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #222;flex-shrink:0}
#skills-header h2{font-size:16px;font-weight:600;color:#4fc3f7}
#skills-close{background:none;border:none;color:#aaa;font-size:22px;cursor:pointer;line-height:1;padding:0 4px}
#skills-body{flex:1;overflow-y:auto;padding:12px;-webkit-overflow-scrolling:touch}
#skills-install{padding:12px;border-top:1px solid #1a1a1a;flex-shrink:0}
#skill-url{width:100%;background:#1a1a1a;border:1px solid #2a2a2a;color:#e8e8e8;padding:10px 14px;border-radius:8px;font-size:14px;margin-bottom:8px;outline:none}
#skill-url:focus{border-color:#4fc3f7}
#install-btn{width:100%;background:#1a6fb5;border:none;color:#fff;padding:10px;border-radius:8px;font-size:14px;cursor:pointer}
.skill-card{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px;padding:12px;margin-bottom:8px}
.skill-name{font-weight:600;color:#e8e8e8;font-size:14px;margin-bottom:4px}
.skill-desc{color:#888;font-size:12px;margin-bottom:8px;line-height:1.4}
.skill-footer{display:flex;align-items:center;gap:8px}
.skill-meta{font-size:11px;color:#555}
.skill-run{margin-left:auto;background:#1a6fb5;border:none;color:#fff;padding:5px 14px;border-radius:12px;font-size:12px;cursor:pointer}
</style>
</head>
<body>
<div id="header">
<h1>⚡ OpenAGI</h1>
<div id="status">Connecting...</div>
</div>
<div id="messages"></div>
<div id="quickbtns">
<button class="qbtn" onclick="send('morning briefing')">☀️ Morning</button>
<button class="qbtn" onclick="send('status')">📊 Status</button>
<button class="qbtn" onclick="send('list goals')">🎯 Goals</button>
<button class="qbtn" onclick="send('what is happening in the world')">🌍 World</button>
<button class="qbtn" onclick="send('evolve')">🧬 Evolve</button>
<button class="qbtn" onclick="openSkills()">🧩 Skills</button>
</div>
<div id="inputbar">
<button id="voicebtn" onclick="toggleVoice()">🎤</button>
<textarea id="input" placeholder="Message OpenAGI..." rows="1" oninput="this.style.height='auto';this.style.height=Math.min(this.scrollHeight,80)+'px'" onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendInput()}"></textarea>
<button id="sendbtn" onclick="sendInput()">↑</button>
</div>
<!-- Skills Modal -->
<div id="skills-modal">
<div id="skills-header">
<h2>🧩 Skills</h2>
<button id="skills-close" onclick="closeSkills()">×</button>
</div>
<div id="skills-body">
<div id="skills-list"><p style="color:#555;text-align:center;padding:20px">Loading...</p></div>
</div>
<div id="skills-install">
<input id="skill-url" placeholder="Install from URL (https://...)">
<button id="install-btn" onclick="installSkill()">📦 Install Skill</button>
</div>
</div>
<script>
const msgs = document.getElementById('messages');
const statusEl = document.getElementById('status');
let ws = null, isListening = false, recognizer = null;

function connect() {
    ws = new WebSocket('ws://' + location.host + '/ws');
    ws.onopen = () => { statusEl.textContent = 'Online'; statusEl.className = 'connected'; };
    ws.onclose = () => { statusEl.textContent = 'Offline'; statusEl.className = ''; setTimeout(connect, 3000); };
    ws.onmessage = (e) => {
        const d = JSON.parse(e.data);
        if (d.type === 'thinking') {
            let el = document.getElementById('thinking_msg');
            if (!el) el = addMsg(d.text || '⚡ Processing...', 'thinking', 'thinking_msg');
        } else if (d.type === 'response') {
            const old = document.getElementById('thinking_msg');
            if (old) old.remove();
            addMsg(d.text, 'agent');
        } else if (d.type === 'proactive') {
            addMsg('💡 ' + d.text, 'agent');
        }
    };
}

function addMsg(text, cls, id) {
    const el = document.createElement('div');
    el.className = 'msg ' + cls;
    if (id) el.id = id;
    el.textContent = text;
    msgs.appendChild(el);
    msgs.scrollTop = msgs.scrollHeight;
    return el;
}

function send(text) {
    if (!text.trim() || !ws || ws.readyState !== 1) return;
    addMsg(text, 'user');
    ws.send(JSON.stringify({type: 'message', text: text}));
    const inp = document.getElementById('input');
    inp.value = '';
    inp.style.height = 'auto';
}

function sendInput() { send(document.getElementById('input').value.trim()); }

function toggleVoice() {
    if (!('webkitSpeechRecognition' in window)) {
        addMsg('Voice not supported in this browser. Try Chrome.', 'agent');
        return;
    }
    const btn = document.getElementById('voicebtn');
    if (!isListening) {
        recognizer = new webkitSpeechRecognition();
        recognizer.lang = 'en-US';
        recognizer.continuous = false;
        recognizer.onresult = (e) => send(e.results[0][0].transcript);
        recognizer.onend = () => { isListening = false; btn.classList.remove('listening'); };
        recognizer.onerror = () => { isListening = false; btn.classList.remove('listening'); };
        recognizer.start();
        isListening = true;
        btn.classList.add('listening');
    } else {
        recognizer.stop();
    }
}

async function openSkills() {
    document.getElementById('skills-modal').classList.add('open');
    const r = await fetch('/api/skills');
    const d = await r.json();
    const list = document.getElementById('skills-list');
    if (!d.skills || d.skills.length === 0) {
        list.innerHTML = '<p style="color:#555;text-align:center;padding:20px">No skills installed yet.</p>';
        return;
    }
    list.innerHTML = d.skills.map(s => `
        <div class="skill-card">
            <div class="skill-name">${s.name}</div>
            <div class="skill-desc">${s.description || 'No description'}</div>
            <div class="skill-footer">
                <span class="skill-meta">v${s.version || '1.0'} · ${s.author || 'local'}</span>
                <button class="skill-run" onclick="runSkill('${s.name}')">▶ Run</button>
            </div>
        </div>
    `).join('');
}

function closeSkills() {
    document.getElementById('skills-modal').classList.remove('open');
}

function runSkill(name) {
    closeSkills();
    send('run skill: ' + name);
}

async function installSkill() {
    const url = document.getElementById('skill-url').value.trim();
    if (!url) return;
    const btn = document.getElementById('install-btn');
    btn.textContent = 'Installing...';
    btn.disabled = true;
    try {
        const r = await fetch('/api/skills/install', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({url: url})
        });
        const d = await r.json();
        if (d.success) {
            document.getElementById('skill-url').value = '';
            addMsg('✅ Skill installed: ' + d.installed, 'agent');
            await openSkills();
        } else {
            addMsg('❌ Install failed: ' + d.error, 'agent');
        }
    } catch (e) {
        addMsg('❌ Error: ' + e.message, 'agent');
    }
    btn.textContent = '📦 Install Skill';
    btn.disabled = false;
}

connect();
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
        """Push proactive message to all connected WebSocket clients."""
        dead = set()
        for ws in self._active_ws:
            try:
                await ws.send_json({"type": "proactive", "text": message})
            except Exception:
                dead.add(ws)
        self._active_ws -= dead

    def start(self, host="0.0.0.0", port=None):
        from fastapi import FastAPI, WebSocket, WebSocketDisconnect
        from fastapi.responses import HTMLResponse
        import uvicorn

        port = port or int(os.getenv("WEBUI_PORT", "8765"))
        app = FastAPI()

        # Wire push function to kernel
        self.kernel._webui_push = self._push_to_all

        @app.get("/", response_class=HTMLResponse)
        async def index():
            return HTML

        @app.get("/api/status")
        async def status():
            from core.goal_persistence import get_pending_count
            tools = self.kernel.executor.registry.list_tools()
            return {
                "online": True,
                "tools": len(tools),
                "tool_names": tools[:10],
                "goals": get_pending_count(),
                "version": "5.0",
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

        @app.post("/api/skills/run")
        async def run_skill(data: dict):
            name = data.get("name", "")
            params = data.get("params", {})
            if not self.kernel.skills:
                return {"success": False, "error": "Skills not loaded"}
            try:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, self.kernel.skills.run_skill, name, params, self.kernel
                )
                return {"success": True, "result": result}
            except Exception as e:
                return {"success": False, "error": str(e)}

        @app.post("/api/skills/install")
        async def install_skill(data: dict):
            url = data.get("url", "")
            if not self.kernel.skills:
                return {"success": False, "error": "Skills not loaded"}
            try:
                name = await asyncio.get_event_loop().run_in_executor(
                    None, self.kernel.skills.install_skill, url
                )
                return {"success": True, "installed": name}
            except Exception as e:
                return {"success": False, "error": str(e)}

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
                        await ws.send_json({"type": "thinking", "text": "⚡ Processing..."})
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

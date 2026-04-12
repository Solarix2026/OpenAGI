"""
webui_server.py — Web UI and phone bridge

python kernel.py web → starts server → prints QR code to terminal
Phone scans QR → opens mobile chat UI → full kernel access via WebSocket

Architecture:
- FastAPI on 0.0.0.0:8765
- GET / → dark mobile chat HTML (inline, no external files needed)
- POST /api/chat → kernel.process(message)
- GET /api/status → system status
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

# HTML inline — complete mobile-first dark UI
HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>OpenAGI</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,system-ui,sans-serif;background:#0a0a0a;color:#e8e8e8;height:100vh;display:flex;flex-direction:column}
#header{background:#111;padding:12px 16px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #222}
#header h1{font-size:18px;font-weight:600;color:#4fc3f7}
#status{font-size:11px;color:#666}
#messages{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px}
.msg{max-width:85%;padding:10px 14px;border-radius:16px;font-size:15px;line-height:1.5;word-break:break-word}
.user{align-self:flex-end;background:#1a6fb5;color:#fff;border-radius:16px 16px 4px 16px}
.agent{align-self:flex-start;background:#1e1e1e;color:#e8e8e8;border-radius:16px 16px 16px 4px;border:1px solid #2a2a2a}
.thinking{color:#666;font-style:italic;font-size:13px}
#quickbtns{display:flex;gap:8px;padding:8px 16px;overflow-x:auto;background:#0f0f0f;border-top:1px solid #1a1a1a}
.qbtn{background:#1a1a1a;border:1px solid #2a2a2a;color:#aaa;padding:6px 12px;border-radius:20px;font-size:12px;white-space:nowrap;cursor:pointer}
.qbtn:hover{border-color:#4fc3f7;color:#4fc3f7}
#inputbar{display:flex;gap:8px;padding:12px 16px;background:#111;border-top:1px solid #1a1a1a}
#input{flex:1;background:#1a1a1a;border:1px solid #2a2a2a;color:#e8e8e8;padding:10px 14px;border-radius:24px;font-size:15px;outline:none}
#input:focus{border-color:#4fc3f7}
#sendbtn{background:#1a6fb5;border:none;color:#fff;width:42px;height:42px;border-radius:50%;font-size:18px;cursor:pointer;flex-shrink:0}
#voicebtn{background:#1a1a1a;border:1px solid #333;color:#aaa;width:42px;height:42px;border-radius:50%;font-size:18px;cursor:pointer;flex-shrink:0}
#voicebtn.listening{background:#c0392b;border-color:#e74c3c;color:#fff;animation:pulse 1s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.6}}
</style>
</head>
<body>
<div id="header"><h1>OpenAGI</h1><div id="status">Connecting...</div></div>
<div id="messages"></div>
<div id="quickbtns">
<button class="qbtn" onclick="send('morning briefing')">Morning</button>
<button class="qbtn" onclick="send('status')">Status</button>
<button class="qbtn" onclick="send('list goals')">Goals</button>
<button class="qbtn" onclick="send('what is happening in the world')">World</button>
<button class="qbtn" onclick="send('evolve')">Evolve</button>
</div>
<div id="inputbar">
<button id="voicebtn" onclick="toggleVoice()">Mic</button>
<input id="input" placeholder="Message OpenAGI..." onkeydown="if(event.key==='Enter')sendInput()">
<button id="sendbtn" onclick="sendInput()">Send</button>
</div>
<script>
const msgs=document.getElementById('messages'),statusEl=document.getElementById('status');
let ws=null,isListening=false,recognizer=null;
function connect(){
  ws=new WebSocket('ws://'+location.host+'/ws');
  ws.onopen=()=>{statusEl.textContent='Connected';statusEl.style.color='#2ecc71';};
  ws.onclose=()=>{statusEl.textContent='Disconnected';statusEl.style.color='#e74c3c';setTimeout(connect,3000);};
  ws.onmessage=(e)=>{
    const d=JSON.parse(e.data);
    if(d.type==='thinking'){
      let el=document.getElementById('thinking_msg');
      if(!el){el=addMsg(d.text,'agent thinking','thinking_msg');}
    } else if(d.type==='response'||d.type==='proactive'){
      const old=document.getElementById('thinking_msg');
      if(old)old.remove();
      addMsg(d.text,d.type==='proactive'?'agent':'agent');
    }
  };
}
function addMsg(text,cls,id){
  const el=document.createElement('div');el.className='msg '+cls;if(id)el.id=id;
  el.textContent=text;msgs.appendChild(el);msgs.scrollTop=msgs.scrollHeight;return el;
}
function send(text){
  if(!text.trim()||!ws||ws.readyState!==1)return;
  addMsg(text,'user');ws.send(JSON.stringify({type:'message',text}));
  document.getElementById('input').value='';
}
function sendInput(){send(document.getElementById('input').value);}
function toggleVoice(){
  if(!('webkitSpeechRecognition'in window)){alert('Voice not supported');return;}
  const btn=document.getElementById('voicebtn');
  if(!isListening){
    recognizer=new webkitSpeechRecognition();recognizer.continuous=false;recognizer.lang='en-US';
    recognizer.onresult=(e)=>send(e.results[0][0].transcript);
    recognizer.onend=()=>{isListening=false;btn.classList.remove('listening');};
    recognizer.start();isListening=true;btn.classList.add('listening');
  } else {recognizer.stop();}
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
            from goal_persistence import get_pending_count
            tools = self.kernel.executor.registry.list_tools()
            return {
                "online": True,
                "tools": len(tools),
                "tool_names": tools[:10],
                "goals": get_pending_count(),
                "version": "5.0"
            }

        @app.post("/api/chat")
        async def chat(data: dict):
            msg = data.get("message", "")
            if not msg:
                return {"response": "No message"}
            import time
            t0 = time.time()
            response = await asyncio.get_event_loop().run_in_executor(None, self.kernel.process, msg)
            return {"response": response, "thinking_time": round(time.time() - t0, 2)}

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
                        await ws.send_json({"type": "thinking", "text": "Processing..."})
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

# Copyright (c) 2026 HackerTMJ
import asyncio, json, socket, os, logging
from pathlib import Path
log=logging.getLogger("WebUI")
HTML="""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>OpenAGI</title>
<style>body{background:#0d1117;color:#c9d1d9;font-family:sans-serif;height:100vh;margin:0;display:grid;grid-template-columns:280px 1fr 300px}
.sidebar,.rightbar{background:#161b22;border-right:1px solid #30363d}
.chat{border-right:1px solid #30363d;display:flex;flex-direction:column}
#messages{flex:1;overflow:auto;padding:16px}
.msg{padding:12px;margin:8px 0;border-radius:8px;max-width:80%}
.msg-user{background:#1f6feb;margin-left:auto}
.msg-agent{background:#161b22;border:1px solid #30363d}
input{flex:1;background:#21262d;border:1px solid #30363d;color:#fff;padding:10px}
button{background:#58a6ff;color:#000;border:none;padding:10px 20px;border-radius:6px;cursor:pointer}
</style>
</head>
<body>
<div class="sidebar"><h3>Files</h3><div id="files"></div></div>
<div class="chat">
<div id="messages"></div>
<div style="display:flex;padding:12px"><input id="in" placeholder="Ask..." onkeypress="if(event.key=='Enter')send()">
<button onclick="send()">Send</button></div>
</div>
<div class="rightbar"><h3>Tools</h3></div>
<script>
let ws=new WebSocket('ws://'+location.host+'/ws')
ws.onmessage=e=>{let d=JSON.parse(e.data);if(d.type=='response')add(d.text,'agent')}
function add(t,who){let m=document.createElement('div');m.className='msg msg-'+who;m.textContent=t;document.getElementById('messages').appendChild(m)}
function send(){let i=document.getElementById('in');ws.send(JSON.stringify({type:'message',text:i.value}));add(i.value,'user');i.value=''}
</script>
</body>
</html>"""

class WebUIServer:
    def __init__(self, kernel):
        self.kernel=kernel
        self._active_ws=set()

    def push_sync(self, msg):
        if not self._active_ws: return
        try:
            loop=asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self._push(msg), loop)
        except: pass

    async def _push(self, msg):
        for ws in list(self._active_ws):
            try: await ws.send_json({"type":"proactive","text":msg})
            except: self._active_ws.discard(ws)

    def start(self, host="0.0.0.0", port=None):
        from fastapi import FastAPI, WebSocket, WebSocketDisconnect
        from fastapi.responses import HTMLResponse
        import uvicorn
        port=port or int(os.getenv("WEBUI_PORT","8765"))
        app=FastAPI()
        if self.kernel: self.kernel._webui_push=self.push_sync

        @app.get("/", response_class=HTMLResponse)
        async def index(): return HTML

        @app.get("/api/files")
        async def files():
            try:
                base=Path("./workspace")
                return {"files":[{"name":p.name,"path":str(p.relative_to(base))} for p in base.rglob("*") if p.is_file()][:50]}
            except: return {"files":[]}

        @app.websocket("/ws")
        async def ws(ws: WebSocket):
            await ws.accept()
            self._active_ws.add(ws)
            try:
                while True:
                    data=json.loads(await ws.receive_text())
                    text=data.get("text","").strip()
                    if not text: continue
                    await ws.send_json({"type":"thinking"})
                    loop=asyncio.get_event_loop()
                    try:
                        r=await asyncio.wait_for(loop.run_in_executor(None,self.kernel.process,text),timeout=120)
                        await ws.send_json({"type":"response","text":r})
                    except: await ws.send_json({"type":"error","text":"Failed"})
            except WebSocketDisconnect: pass
            finally: self._active_ws.discard(ws)

        print(f"OpenAGI: http://{socket.getaddrinfo('8.8.8.8',80)[0][4][0] if socket.socket(socket.AF_INET,socket.SOCK_DGRAM).connect(('8.8.8.8',80)) or True else '127.0.0.1'}:{port}")
        uvicorn.run(app,host=host,port=port,log_level="warning")

import asyncio, json, socket, os, logging
import qrcode
from pathlib import Path
log=logging.getLogger("WebUI")
HTML="""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>OpenAGI</title>
<style>
body{background:#0d1117;color:#c9d1d9;font-family:-apple-system,BlinkMacSystemFont,sans-serif;height:100vh;margin:0;display:flex}
.sidebar{width:280px;background:#161b22;border-right:1px solid #30363d;overflow:auto;padding:16px}
.main{flex:1;display:flex;flex-direction:column}
#messages{flex:1;overflow:auto;padding:20px}
.msg{padding:12px 16px;margin:8px 0;border-radius:8px;max-width:80%;line-height:1.5}
.msg-user{background:#1f6feb;margin-left:auto;color:#fff}
.msg-agent{background:#161b22;border:1px solid #30363d}
.input-area{display:flex;padding:16px;border-top:1px solid #30363d;gap:12px}
input{flex:1;background:#0d1117;border:1px solid #30363d;color:#e6edf3;padding:12px 16px;border-radius:8px;font-size:14px}
input:focus{border-color:#58a6ff;outline:none}
button{background:#238636;color:#fff;border:none;padding:12px 24px;border-radius:8px;cursor:pointer;font-size:14px;font-weight:500}
button:hover{background:#2ea043}
.panel-header{font-size:12px;font-weight:600;color:#8b949e;text-transform:uppercase;padding:8px 0;border-bottom:1px solid #30363d;margin-bottom:12px}
.status{display:flex;align-items:center;gap:8px;margin-bottom:16px;padding:8px 12px;background:#21262d;border-radius:6px;font-size:13px}
.status-dot{width:8px;height:8px;border-radius:50%;background:#da3633}
.status-dot.connected{background:#238636}
::-webkit-scrollbar{width:8px}
::-webkit-scrollbar-thumb{background:#30363d;border-radius:4px}
</style>
</head>
<body>
<div class="sidebar">
  <div class="panel-header">OpenAGI IDE</div>
  <div class="status"><span class="status-dot" id="status-dot"></span><span id="status-text">Connecting...</span></div>
  <div class="panel-header">Files</div>
  <div style="padding:8px;color:#8b949e;font-size:13px" id="file-list">Loading...</div>
</div>
<div class="main">
  <div id="messages"></div>
  <div class="input-area">
    <input type="text" id="msg-input" placeholder="Ask anything..." onkeypress="if(event.key==='Enter')send()">
    <button onclick="send()">Send</button>
  </div>
</div>
<script>
let ws=null;
function setStatus(c,t){
  const d=document.getElementById('status-dot'),s=document.getElementById('status-text');
  d.className=c?'status-dot connected':'status-dot';
  s.textContent=t;
}
function connect(){
  ws=new WebSocket('ws://'+location.host+'/ws');
  ws.onopen=()=>{setStatus(true,'Connected');add('Connected to OpenAGI','agent');};
  ws.onclose=()=>{setStatus(false,'Disconnected');setTimeout(connect,3000);};
  ws.onmessage=(e)=>{
    let d=JSON.parse(e.data);
    if(d.type==='thinking')add('Thinking...','agent');
    else if(d.type==='response'){removeThink();add(d.text,'agent');}
    else if(d.type==='error'){removeThink();add('Error: '+d.text,'agent');}
  };
}
function add(t,who){
  let m=document.getElementById('messages'),d=document.createElement('div');
  d.className='msg msg-'+who;
  d.innerHTML=t.replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/`([^`]+)`/g,'<code style="background:rgba(0,0,0,.3);padding:2px 6px;border-radius:4px">$1</code>').replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>').replace(/>n/g,'</p><p>');
  m.appendChild(d);m.scrollTop=999999;
}
function removeThink(){let t=document.querySelector('.msg:last-child');if(t&&t.textContent==='Thinking...')t.remove();}
function send(){let i=document.getElementById('msg-input'),t=i.value.trim();if(!t||!ws)return;add(t,'user');ws.send(JSON.stringify({type:'message',text:t}));i.value='';}
connect();
</script>
</body>
</html>
"""


class WebUIServer:
    def __init__(self, kernel):
        self.kernel = kernel
        self._active_ws = set()

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return socket.gethostbyname(socket.gethostname()) or "127.0.0.1"

    def push_sync(self, msg):
        if not self._active_ws:
            return
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self._push(msg), loop)
        except:
            pass

    async def _push(self, msg):
        dead = set()
        for ws in self._active_ws:
            try:
                await ws.send_json({"type": "proactive", "text": msg})
            except:
                dead.add(ws)
        self._active_ws -= dead

    def start(self, host="0.0.0.0", port=None):
        from fastapi import FastAPI, WebSocket, WebSocketDisconnect
        from fastapi.responses import HTMLResponse, JSONResponse
        import uvicorn

        port = port or int(os.getenv("WEBUI_PORT", "8765"))
        app = FastAPI()

        if self.kernel:
            self.kernel._webui_push = self.push_sync

        @app.get("/", response_class=HTMLResponse)
        async def index():
            return HTML

        @app.get("/api/status")
        async def status():
            return {"status": "ok", "connections": len(self._active_ws)}

        @app.websocket("/ws")
        async def ws_endpoint(ws: WebSocket):
            await ws.accept()
            self._active_ws.add(ws)
            try:
                while True:
                    data = json.loads(await ws.receive_text())
                    text = data.get("text", "").strip()
                    if not text:
                        continue
                    await ws.send_json({"type": "thinking"})
                    loop = asyncio.get_event_loop()
                    try:
                        r = await asyncio.wait_for(
                            loop.run_in_executor(None, self.kernel.process, text),
                            timeout=120
                        )
                        await ws.send_json({"type": "response", "text": r})
                    except asyncio.TimeoutError:
                        await ws.send_json({"type": "error", "text": "Timeout"})
                    except Exception as e:
                        await ws.send_json({"type": "error", "text": str(e)})
            except WebSocketDisconnect:
                pass
            finally:
                self._active_ws.discard(ws)

        # Get and display local IP + QR code
        ip = self._get_local_ip()
        url = f"http://{ip}:{port}"

        print("\n" + "="*50)
        print("  OpenAGI WebUI Ready!")
        print("="*50)
        print(f"\n  ➡️  {url}")
        print(f"  📡  Port: {port}")
        print(f"  📐  IP: {ip}")

        try:
            qr = qrcode.QRCode(box_size=1, border=1)
            qr.add_data(url)
            qr.make()
            print("\n  📱  Scan QR Code:")
            qr.print_ascii(invert=True)
        except Exception:
            pass

        print("="*50 + "\n")

        uvicorn.run(app, host=host, port=port, log_level="warning")

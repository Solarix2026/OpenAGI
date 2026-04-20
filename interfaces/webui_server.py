# Copyright (c) 2026 Solarix2026
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI
import asyncio, json, socket, os, logging, threading
from pathlib import Path

log = logging.getLogger("WebUI")

# HTML template moved to separate file for maintainability
_TEMPLATE_PATH = Path(__file__).parent / "webui_template.html"
try:
    HTML_V3 = _TEMPLATE_PATH.read_text(encoding="utf-8") if _TEMPLATE_PATH.exists() else "<h1>Template missing</h1>"
except Exception as e:
    log.warning(f"Failed to load template: {e}")
    HTML_V3 = "<h1>Template load error</h1>"

HTML_TEMPLATE = HTML_V3  # For V2 compatibility


# In-memory log storage (ring buffer)
class LogBuffer:
    """Thread-safe ring buffer for logs."""
    def __init__(self, max_size=1000):
        self._logs = []
        self._max_size = max_size
        self._lock = threading.Lock()

    def add(self, log_entry: dict):
        with self._lock:
            self._logs.append(log_entry)
            if len(self._logs) > self._max_size:
                self._logs.pop(0)

    def get_logs(self, level_filter=None, module_filter=None, limit=100, offset=0):
        with self._lock:
            logs = self._logs.copy()

        if level_filter and level_filter != 'all':
            logs = [l for l in logs if l.get('level') == level_filter]
        if module_filter and module_filter != 'all':
            logs = [l for l in logs if l.get('module') == module_filter]

        # Return newest first (reverse)
        logs = logs[::-1]
        return logs[offset:offset + limit]

    def clear(self):
        with self._lock:
            self._logs = []

    def get_modules(self):
        """Return unique module names."""
        with self._lock:
            return sorted(set(l.get('module', 'Unknown') for l in self._logs))


class WebSocketLogHandler(logging.Handler):
    """Logging handler that broadcasts to WebSocket clients."""
    def __init__(self, log_buffer: LogBuffer, active_ws_set: set):
        super().__init__()
        self.log_buffer = log_buffer
        self.active_ws = active_ws_set
        self.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(message)s"))

    def emit(self, record: logging.LogRecord):
        try:
            # Map Python log levels to frontend levels
            level_map = {
                'DEBUG': 'debug',
                'INFO': 'info',
                'WARNING': 'warning',
                'ERROR': 'error',
                'CRITICAL': 'error',
            }

            log_entry = {
                'id': f"log-{record.created}-{record.lineno}",
                'timestamp': int(record.created * 1000),  # JS timestamp in ms
                'level': level_map.get(record.levelname, 'info'),
                'module': record.name,
                'message': self.format(record),
                'details': f"File: {record.filename}:{record.lineno}",
            }

            # Store in buffer
            self.log_buffer.add(log_entry)

            # Broadcast to WebSocket clients (async-safe via thread)
            if self.active_ws:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.run_coroutine_threadsafe(
                            self.broadcast_log(log_entry), loop
                        )
                except Exception:
                    pass
        except Exception:
            self.handleError(record)

    async def broadcast_log(self, log_entry: dict):
        """Broadcast log to all connected WebSocket clients."""
        dead = set()
        for ws in self.log_buffer._active_ws_ref if hasattr(self.log_buffer, '_active_ws_ref') else []:
            try:
                await ws.send_json({'type': 'log', 'log': log_entry})
            except Exception:
                dead.add(ws)


class WebUIServer:
    def __init__(self, kernel):
        self.kernel = kernel
        self._active_ws = set()
        self._log_buffer = LogBuffer(max_size=1000)
        self._log_buffer._active_ws_ref = self._active_ws  # Reference for handler

        # Set up WebSocket log handler
        self._ws_log_handler = WebSocketLogHandler(self._log_buffer, self._active_ws)
        self._ws_log_handler.setLevel(logging.DEBUG)

        # Attach to root logger to capture all logs
        root_logger = logging.getLogger()
        root_logger.addHandler(self._ws_log_handler)

        # Store reference for cleanup
        self._log_handler = self._ws_log_handler

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def push_sync(self, msg: str):
        """Thread-safe push from background threads (ProactiveEngine etc.)."""
        if not self._active_ws:
            return
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self._push_to_all(msg), loop)
        except Exception as e:
            log.debug(f"push_sync failed: {e}")

    async def _push_to_all(self, message: str):
        dead = set()
        for ws in self._active_ws:
            try:
                await ws.send_json({"type": "proactive", "text": message})
            except Exception:
                dead.add(ws)
        self._active_ws -= dead

    def start(self, host="0.0.0.0", port=None):
        from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
        from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
        from fastapi.staticfiles import StaticFiles
        import uvicorn

        self.app = FastAPI()
        port = port or int(os.getenv("WEBUI_PORT", "8765"))

        if self.kernel:
            self.kernel._webui_push = self.push_sync

        # Try to serve React frontend, fall back to embedded HTML
        frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
        index_html = frontend_dist / "index.html"

        # Debug logging
        debug_msg = f"Frontend check: dist={frontend_dist} exists={frontend_dist.exists()} index_html={index_html} exists={index_html.exists() if frontend_dist.exists() else 'N/A'}\n"
        with open(Path(__file__).parent / "debug_frontend.log", "w") as f:
            f.write(debug_msg)

        log.info(debug_msg.strip())

        @self.app.get("/", response_class=HTMLResponse)
        async def index():
            if frontend_dist.exists() and index_html.exists():
                log.info("[WebUI] Serving React frontend from " + str(index_html))
                with open(index_html, "r", encoding="utf-8") as f:
                    return f.read()
            log.info("[WebUI] Frontend not found, serving fallback HTML_V3")
            return HTML_V3

        # Mount static files if frontend is built
        if frontend_dist.exists():
            try:
                assets_dir = frontend_dist / "assets"
                if assets_dir.exists():
                    self.app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
                    log.info(f"[WebUI] Mounted frontend assets from {assets_dir}")
            except Exception as e:
                log.warning(f"[WebUI] Failed to mount static assets: {e}")

        @self.app.get("/health")
        async def health():
            """Health check endpoint for debugging connection issues."""
            return {
                "status": "ok",
                "kernel": "ready" if self.kernel else "not_initialized",
                "ws_clients": len(self._active_ws)
            }

        @self.app.get("/api/status")
        async def status():
            tools = self.kernel.executor.registry.list_tools() if self.kernel else []
            return {"online": True, "tools": len(tools), "tool_names": tools[:35]}

        @self.app.get("/api/history")
        async def history():
            """Return conversation history from episodic memory."""
            if not self.kernel:
                return {"messages": []}
            try:
                events = self.kernel.memory.get_recent_timeline(limit=100)
                messages = []
                for e in reversed(events):
                    etype = e.get("event_type", "")
                    content = (e.get("content") or "").strip()
                    if not content or len(content) < 2:
                        continue
                    if etype == "user_message":
                        messages.append({"role": "user", "content": content})
                    elif etype in ("assistant_response", "agent_response"):
                        messages.append({"role": "assistant", "content": content})
                return {"messages": messages[-30:], "total_found": len(messages)}
            except Exception as ex:
                log.error(f"History failed: {ex}")
                return {"messages": [], "error": str(ex)}

        @self.app.get("/api/sessions")
        async def list_sessions():
            """List all chat sessions."""
            if not self.kernel or not self.kernel.memory:
                return {"sessions": [], "current": None}
            try:
                sessions = self.kernel.memory.list_sessions(limit=20)
                current = getattr(self.kernel, '_current_session_id', None)
                return {"sessions": sessions, "current": current}
            except Exception as e:
                return {"sessions": [], "current": None, "error": str(e)}

        @self.app.post("/api/sessions/{session_id}/load")
        async def load_session_api(session_id: str):
            """Load a chat session."""
            if not self.kernel or not hasattr(self.kernel, 'load_session'):
                return {"success": False, "error": "load_session not available"}
            try:
                ok = self.kernel.load_session(session_id)
                if ok:
                    return {"success": True, "session_id": session_id}
                return {"success": False, "error": "Session not found"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.app.get("/api/skills")
        async def list_skills():
            if not self.kernel or not self.kernel.skills:
                return {"skills": []}
            skills = []
            for name in self.kernel.skills.list_skills():
                spec = self.kernel.skills.get_skill(name)
                if spec:
                    skills.append({"name": name, "description": spec.get("description", "")})
            return {"skills": skills}

        @self.app.get("/api/goals")
        async def list_goals():
            from core.goal_persistence import load_goal_queue
            return {"goals": load_goal_queue()[:20]}

        @self.app.get("/api/memory/recent")
        async def recent_memory():
            if not self.kernel:
                return {"events": []}
            try:
                events = self.kernel.memory.get_recent_timeline(limit=15)
                return {"events": events}
            except Exception as ex:
                return {"events": [], "error": str(ex)}

        @self.app.post("/api/memory/clear")
        async def clear_memory():
            if self.kernel:
                self.kernel.memory._faiss_index = None
                self.kernel.memory._faiss_texts = []
                self.kernel.memory._faiss_dirty = True
            return {"success": True}

        @self.app.get("/api/capabilities")
        async def capabilities():
            default = {"memory": 0.85, "reasoning": 0.70, "planning": 0.65,
                       "coding": 0.60, "computer": 0.45, "browser": 0.45, "evolution": 0.68}
            if self.kernel and self.kernel.meta:
                try:
                    matrix = self.kernel.meta._matrix
                    return {k: round(min(v / 5.0, 1.0), 2) for k, v in list(matrix.items())[:7]}
                except Exception:
                    pass
            return default

        @self.app.get("/api/logs")
        async def get_logs(
            level: str = 'all',
            module: str = 'all',
            limit: int = 100,
            offset: int = 0
        ):
            """Return in-memory logs with filtering."""
            logs = self._log_buffer.get_logs(
                level_filter=level,
                module_filter=module,
                limit=limit,
                offset=offset
            )
            return {
                "logs": logs,
                "total": len(logs),
                "modules": self._log_buffer.get_modules()
            }

        @self.app.post("/api/logs/clear")
        async def clear_logs_api():
            """Clear all stored logs."""
            self._log_buffer.clear()
            return {"success": True, "message": "Logs cleared"}

        @self.app.get("/api/agents")
        async def list_agents():
            """List hired agent team."""
            if not self.kernel or not hasattr(self.kernel, 'org') or not self.kernel.org:
                return {"team": []}
            try:
                return {"team": self.kernel.org.list_team()}
            except Exception:
                return {"team": []}

        @self.app.get("/api/settings")
        async def get_settings():
            """Return current settings for the UI."""
            if not self.kernel:
                return {"mode": "auto", "proactive_enabled": False, "tts_lang": "auto"}

            current_mode = "auto"
            try:
                if hasattr(self.kernel, 'mode_manager') and self.kernel.mode_manager:
                    current_mode = str(self.kernel.mode_manager.current).lower()
            except Exception:
                pass

            proactive_enabled = False
            try:
                if self.kernel.proactive and hasattr(self.kernel.proactive, '_thread'):
                    proactive_enabled = self.kernel.proactive._thread and self.kernel.proactive._thread.is_alive()
            except Exception:
                pass

            return {
                "mode": current_mode,
                "proactive_enabled": proactive_enabled,
                "tts_lang": "zh" if os.getenv("TTS_VOICE_ZH") else "en",
                "model_main": os.getenv("NVIDIA_MAIN_MODEL", "moonshotai/kimi-k2.5"),
                "model_fast": os.getenv("NVIDIA_FAST_MODEL", "moonshotai/kimi-k2.5"),
                "groq_key_set": bool(os.getenv("GROQ_API_KEY")),
                "nvidia_key_set": bool(os.getenv("NVIDIA_API_KEY")),
                "telegram_set": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
                "user_city": os.getenv("USER_CITY", ""),
                "max_history": int(os.getenv("MAX_HISTORY_TURNS", "8")),
                "wake_word": os.getenv("WAKE_WORD", "jarvis"),
                "webui_port": int(os.getenv("WEBUI_PORT", "8765")),
                "version": "5.5.0",
            }

        @self.app.post("/api/settings")
        async def update_settings(request: Request):
            """Apply settings changes from UI."""
            data = await request.json()
            changed = []
            env_path = Path(".env")

            def update_env(key: str, value: str):
                """Update a key in .env file."""
                if env_path.exists():
                    lines = env_path.read_text().splitlines()
                    found = False
                    for i, line in enumerate(lines):
                        if line.startswith(f"{key}="):
                            lines[i] = f"{key}={value}"
                            found = True
                            break
                    if not found:
                        lines.append(f"{key}={value}")
                    env_path.write_text("\n".join(lines) + "\n")
                os.environ[key] = value

            # Mode
            if "mode" in data and self.kernel and hasattr(self.kernel, 'mode_manager'):
                try:
                    from core.mode_manager import Mode
                    mode_map = {"auto": Mode.AUTO, "code": Mode.CODE, "reason": Mode.REASON,
                                "plan": Mode.PLAN, "research": Mode.RESEARCH}
                    mode_val = mode_map.get(data["mode"], Mode.AUTO)
                    self.kernel.mode_manager.set_mode(mode_val)
                    changed.append(f"mode → {data['mode']}")
                except Exception as e:
                    log.warning(f"Mode change failed: {e}")

            # Proactive toggle
            if "proactive_enabled" in data and self.kernel:
                try:
                    if self.kernel.proactive:
                        if data["proactive_enabled"]:
                            self.kernel.proactive.start()
                            changed.append("proactive → started")
                        else:
                            self.kernel.proactive.stop()
                            changed.append("proactive → stopped")
                except Exception as e:
                    log.warning(f"Proactive toggle failed: {e}")

            # API Keys (write to .env)
            for key_name in ["GROQ_API_KEY", "NVIDIA_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]:
                if key_name in data and data[key_name]:
                    update_env(key_name, data[key_name])
                    changed.append(f"{key_name}=***")

            # Model selection
            if "model_main" in data:
                update_env("NVIDIA_MAIN_MODEL", data["model_main"])
                from core import llm_gateway
                llm_gateway.NVIDIA_MAIN_MODEL = data["model_main"]
                llm_gateway._nvidia_client = None
                changed.append(f"model → {data['model_main']}")

            # User settings
            if "user_city" in data:
                update_env("USER_CITY", data["user_city"])
                changed.append(f"city → {data['user_city']}")
            if "max_history" in data:
                update_env("MAX_HISTORY_TURNS", str(data["max_history"]))
                import core.kernel_impl as ki
                ki.MAX_HISTORY_TURNS = int(data["max_history"])
                changed.append(f"history → {data['max_history']}")
            if "wake_word" in data:
                update_env("WAKE_WORD", data["wake_word"])
                changed.append(f"wake_word → {data['wake_word']}")
            if "tts_lang" in data:
                voice = "zh-CN-YunxiNeural" if data["tts_lang"] == "zh" else "en-GB-RyanNeural"
                if data["tts_lang"] == "zh":
                    update_env("TTS_VOICE_ZH", voice)
                else:
                    update_env("TTS_VOICE_EN", voice)
                changed.append(f"tts → {data['tts_lang']}")

            log.info(f"[SETTINGS] Updated: {changed}")
            return {"success": True, "changed": changed}

        @self.app.get("/api/file")
        async def read_file(path: str):
            """Read a file for preview."""
            try:
                safe_base = Path(".").resolve()
                target = (safe_base / path).resolve()
                # Security: only allow files within project directory
                if not str(target).startswith(str(safe_base)):
                    return {"error": "Access denied"}
                if target.exists() and target.is_file():
                    content = target.read_text(encoding="utf-8", errors="replace")
                    return {"path": path, "content": content[:50000]}
                return {"error": "File not found"}
            except Exception as e:
                return {"error": str(e)}

        @self.app.websocket("/ws")
        async def ws_endpoint(ws: WebSocket):
            try:
                await ws.accept()
                log.info("[WS] Client connected")
                self._active_ws.add(ws)

                # Send initial history to new client
                try:
                    # Send recent logs
                    recent_logs = self._log_buffer.get_logs(limit=100)
                    for log_entry in recent_logs:
                        await ws.send_json({"type": "log", "log": log_entry})

                    # Send recent memory events
                    if self.kernel and hasattr(self.kernel, 'memory'):
                        try:
                            mem_events = self.kernel.memory.get_recent_timeline(limit=50)
                            for evt in reversed(mem_events):
                                await ws.send_json({"type": "memory_event", "event": evt})
                        except Exception as e:
                            log.debug(f"[WS] Failed to send memory history: {e}")

                    # Send goals
                    try:
                        from core.goal_persistence import load_goal_queue
                        goals = load_goal_queue()
                        pending = [g for g in goals if g.get("status") == "pending"]
                        await ws.send_json({"type": "goals_init", "goals": goals, "pending_count": len(pending)})
                    except Exception as e:
                        log.debug(f"[WS] Failed to send goals: {e}")

                    # Send agent team status
                    if self.kernel and hasattr(self.kernel, 'agent_org'):
                        try:
                            team = self.kernel.agent_org.list_team()
                            await ws.send_json({"type": "agents_init", "team": team})
                        except Exception as e:
                            log.debug(f"[WS] Failed to send agents: {e}")

                except Exception as e:
                    log.debug(f"[WS] Failed to send initial history: {e}")

                try:
                    while True:
                        try:
                            raw = await ws.receive_text()
                        except Exception as e:
                            log.debug(f"[WS] receive_text failed: {e}")
                            break

                        try:
                            data = json.loads(raw)
                        except json.JSONDecodeError:
                            log.warning(f"[WS] Invalid JSON: {raw[:100]}")
                            continue

                        # Handle new_chat and load_session requests
                        if data.get("type") == "new_chat":
                            if self.kernel and hasattr(self.kernel, 'new_chat'):
                                try:
                                    new_id = await asyncio.get_event_loop().run_in_executor(None, self.kernel.new_chat)
                                    await ws.send_json({
                                        "type": "new_chat_started",
                                        "session_id": new_id,
                                        "message": "New conversation started. Your memories and profile are preserved."
                                    })
                                except Exception as e:
                                    log.warning(f"[WS] new_chat failed: {e}")
                                    await ws.send_json({"type": "error", "message": str(e)})
                            else:
                                await ws.send_json({"type": "error", "message": "new_chat not available"})
                            continue

                        if data.get("type") == "load_session":
                            session_id = data.get("session_id", "")
                            if session_id and self.kernel and hasattr(self.kernel, 'load_session'):
                                try:
                                    ok = await asyncio.get_event_loop().run_in_executor(None, self.kernel.load_session, session_id)
                                    if ok:
                                        messages = await asyncio.get_event_loop().run_in_executor(None, self.kernel.memory.get_session_messages, session_id, 50)
                                        await ws.send_json({
                                            "type": "session_loaded",
                                            "session_id": session_id,
                                            "messages": messages
                                        })
                                    else:
                                        await ws.send_json({"type": "error", "message": "Session not found"})
                                except Exception as e:
                                    log.warning(f"[WS] load_session failed: {e}")
                                    await ws.send_json({"type": "error", "message": str(e)})
                            else:
                                await ws.send_json({"type": "error", "message": "load_session not available"})
                            continue

                        if data.get("type") == "message":
                            text = data.get("text", "").strip()
                            if not text:
                                continue

                            try:
                                await ws.send_json({"type": "thinking"})
                            except Exception as e:
                                log.warning(f"[WS] Failed to send thinking: {e}")
                                break

                            loop = asyncio.get_event_loop()
                            try:
                                response = await asyncio.wait_for(
                                    loop.run_in_executor(None, self.kernel.process, text),
                                    timeout=120
                                )
                                try:
                                    await ws.send_json({"type": "response", "text": response})
                                except Exception as e:
                                    log.warning(f"[WS] Failed to send response: {e}")
                            except asyncio.TimeoutError:
                                log.warning("[WS] Timeout in kernel.process")
                                try:
                                    await ws.send_json({"type": "response", "text": "Request timed out after 120s."})
                                except:
                                    pass
                            except Exception as ex:
                                log.error(f"[WS] kernel.process error: {ex}", exc_info=True)
                                try:
                                    await ws.send_json({"type": "response", "text": f"Error: {str(ex)[:200]}"})
                                except:
                                    pass
                except WebSocketDisconnect:
                    log.info("[WS] Client disconnected")
                finally:
                    self._active_ws.discard(ws)
            except Exception as e:
                log.error(f"[WS] Accept failed: {e}", exc_info=True)

        # Print connection info
        ip = self._get_local_ip()
        url = f"http://{ip}:{port}"
        try:
            import qrcode
            qr = qrcode.QRCode(box_size=2, border=1)
            qr.add_data(url)
            qr.make(fit=True)
            qr.print_ascii(invert=True)
        except Exception:
            pass
        log.info(f"Web UI: {url}")
        uvicorn.run(self.app, host=host, port=port, log_level="warning")

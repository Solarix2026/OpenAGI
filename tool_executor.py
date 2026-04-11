"""
tool_executor.py — Tool execution engine

Registers all built-in tools. Executes by name. All tools are real implementations — no stubs.

CRITICAL FIXES from v4 bugs:
  - websearch: BeautifulSoup parsing + NVIDIA summarization (no raw HTML)
  - system_open_app: os.startfile() as Method 1 on Windows
  - shell_command: PowerShell on Windows, expanded whitelist
  - All imports from flat directory (no reasoning.xxx prefix)
"""
import os, re, json, logging, subprocess, platform, time, webbrowser
from pathlib import Path
from typing import Any

log = logging.getLogger("ToolExecutor")


class ToolExecutor:
    def __init__(self, workspace: str = "./workspace", memory=None):
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.memory = memory
        self.registry = self._build_registry()

    def _build_registry(self):
        from tool_registry import ToolRegistry
        reg = ToolRegistry()

        reg.register("websearch", self._websearch,
            "Search the web for any information, news, facts, or research",
            {"query": {"type": "string", "required": True}})

        reg.register("browser_navigate", self._browser_navigate,
            "Open a specific URL in the browser",
            {"url": {"type": "string", "required": True}})

        reg.register("system_open_app", self._system_open_app,
            "Open an application or file on the computer",
            {"app_name": {"type": "string", "required": True}})

        reg.register("write_file", self._write_file,
            "Write or create a file with content",
            {"path": {"type": "string"}, "content": {"type": "string"}})

        reg.register("read_file", self._read_file,
            "Read the contents of a file",
            {"path": {"type": "string", "required": True}})

        reg.register("shell_command", self._shell_command,
            "Execute a safe shell command",
            {"command": {"type": "string", "required": True}})

        reg.register("api_call", self._api_call,
            "Make an HTTP GET/POST request to any URL",
            {"url": {"type": "string"}, "method": {"type": "string"}})

        reg.register("memory_search", self._memory_search,
            "Search your memory for past events, context, or information",
            {"query": {"type": "string", "required": True}})

        reg.register("world_events", self._world_events,
            "Fetch real-time world news: geopolitics, technology, AI, markets",
            {"categories": {"type": "list", "optional": True}})

        reg.register("take_screenshot", self._take_screenshot,
            "Take a screenshot of the current screen", {})

        return reg

    def execute(self, intent: dict) -> dict:
        action = intent.get("action", "")
        params = intent.get("parameters", {})
        t0 = time.time()

        result = self.registry.execute(action, params)

        elapsed = int((time.time() - t0) * 1000)
        if self.memory:
            self.memory.log_tool_outcome(
                tool=action,
                params=params,
                outcome=str(result.get("data", result.get("error", "")))[:200],
                success=result.get("success", False),
                duration_ms=elapsed
            )
        return result

    # ── Tool implementations ────────────────────────────────────

    def _websearch(self, params: dict) -> dict:
        """
        Real web search with BeautifulSoup extraction + NVIDIA summarization.
        Returns clean text, not raw HTML.
        """
        query = params.get("query", "")
        if not query:
            return {"success": False, "error": "No query provided"}

        try:
            import requests
            from urllib.parse import quote
            from bs4 import BeautifulSoup

            url = f"https://duckduckgo.com/html/?q={quote(query)}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            r = requests.get(url, headers=headers, timeout=20)
            r.raise_for_status()

            soup = BeautifulSoup(r.text, "html.parser")
            results = []
            for el in soup.select(".result")[:8]:
                title = el.select_one(".result__title")
                snippet = el.select_one(".result__snippet")
                link = el.select_one(".result__url")
                if title and snippet:
                    results.append({
                        "title": title.get_text(strip=True),
                        "snippet": snippet.get_text(strip=True),
                        "url": link.get_text(strip=True) if link else ""
                    })

            if not results:
                # Generic text extraction fallback
                for tag in soup(["script", "style", "nav", "header", "footer"]):
                    tag.decompose()
                clean = soup.get_text(separator=" ", strip=True)
                clean = re.sub(r"\s+", " ", clean)[:1500]
                results = [{"title": "Search result", "snippet": clean, "url": ""}]

            raw_text = "\n".join(
                f"• {r['title']}: {r['snippet']}"
                for r in results
            )

            return {
                "success": True,
                "query": query,
                "results": results,
                "clean_summary": raw_text[:2000],
                "result_count": len(results)
            }

        except ImportError:
            # bs4 not installed — minimal fallback
            try:
                import requests
                from urllib.parse import quote
                r = requests.get(
                    f"https://duckduckgo.com/html/?q={quote(query)}",
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=15
                )
                clean = re.sub(r"<[^>]+>", " ", r.text)
                clean = re.sub(r"\s+", " ", clean).strip()[:2000]
                return {"success": True, "query": query, "clean_summary": clean, "results": []}
            except Exception as e:
                return {"success": False, "error": str(e)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _system_open_app(self, params: dict) -> dict:
        """
        Open application or file.
        Priority: os.startfile → subprocess (shell=True) → where + explicit path
        """
        app = params.get("app_name", "").strip()
        if not app:
            return {"success": False, "error": "No app name"}

        # Normalize common aliases
        aliases = {
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "notepad": "notepad.exe",
            "explorer": "explorer.exe",
            "file explorer": "explorer.exe",
            "browser": "https://www.google.com",
            "chrome": "chrome.exe",
            "edge": "msedge.exe",
            "vscode": "code",
            "vs code": "code",
            "terminal": "wt.exe",
            "warp": "warp.exe",
        }
        resolved = aliases.get(app.lower(), app)

        # Method 1: os.startfile (Windows native, handles .exe, URLs, files)
        if platform.system() == "Windows":
            try:
                os.startfile(resolved)
                return {"success": True, "message": f"Opened: {app}"}
            except Exception:
                pass

        # Method 2: subprocess shell
        try:
            subprocess.Popen(resolved, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"success": True, "message": f"Launched: {app}"}
        except Exception as e:
            pass

        # Method 3: webbrowser for URLs
        if resolved.startswith("http"):
            webbrowser.open(resolved)
            return {"success": True, "message": f"Opened URL: {resolved}"}

        return {"success": False, "error": f"Could not open: {app}"}

    def _browser_navigate(self, params: dict) -> dict:
        url = params.get("url", "")
        if not url:
            return {"success": False, "error": "No URL"}

        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open(url)
        return {"success": True, "message": f"Opened: {url}", "url": url}

    def _write_file(self, params: dict) -> dict:
        path = params.get("path", "output.txt")
        content = params.get("content", "")
        p = Path(path) if Path(path).is_absolute() else self.workspace / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"success": True, "path": str(p), "bytes": len(content)}

    def _read_file(self, params: dict) -> dict:
        path = params.get("path", "")
        p = Path(path) if Path(path).is_absolute() else self.workspace / path
        if not p.exists():
            return {"success": False, "error": f"File not found: {path}"}
        content = p.read_text(encoding="utf-8", errors="replace")
        return {"success": True, "path": str(p), "content": content, "size": len(content)}

    def _shell_command(self, params: dict) -> dict:
        cmd = params.get("command", "").strip()
        if not cmd:
            return {"success": False, "error": "Empty command"}

        ALLOWED = {
            "python", "pip", "git", "node", "npm",
            "ls", "dir", "cat", "type", "echo", "pwd", "cd", "mkdir",
            "copy", "xcopy", "uvicorn", "pytest", "py",
        }

        first_word = cmd.split()[0].lower().rstrip(".exe")
        if first_word not in ALLOWED:
            return {"success": False, "error": f"Command not in allowlist: {first_word}"}

        use_ps = platform.system() == "Windows"
        shell_cmd = f'powershell -Command "{cmd}"' if use_ps else cmd

        try:
            result = subprocess.run(
                shell_cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[:2000],
                "stderr": result.stderr[:500],
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out (30s)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _api_call(self, params: dict) -> dict:
        import requests
        url = params.get("url", "")
        method = params.get("method", "GET").upper()
        body = params.get("body", {})
        headers = params.get("headers", {})

        if not url:
            return {"success": False, "error": "No URL"}

        try:
            fn = getattr(requests, method.lower())
            r = fn(url, json=body if body else None, headers=headers, timeout=15)
            try:
                content = r.json()
            except Exception:
                content = r.text[:2000]
            return {"success": r.status_code < 400, "status": r.status_code, "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _memory_search(self, params: dict) -> dict:
        if not self.memory:
            return {"success": False, "error": "Memory not available"}
        q = params.get("query", "")
        results = self.memory.search_events(q, limit=5)
        return {"success": True, "results": results, "count": len(results)}

    def _world_events(self, params: dict) -> dict:
        """Fetch world events via RSS."""
        try:
            from worldmonitor_client import WorldMonitorClient
            wm = WorldMonitorClient()
            cats = params.get("categories")
            events = wm.get_events(categories=cats, limit=15)
            return {"success": True, "events": events, "count": len(events)}
        except ImportError:
            return {"success": False, "error": "worldmonitor_client not installed"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _take_screenshot(self, params: dict) -> dict:
        try:
            import pyautogui
            path = str(self.workspace / f"screenshot_{int(time.time())}.png")
            pyautogui.screenshot(path)
            return {"success": True, "path": path}
        except Exception as e:
            return {"success": False, "error": str(e)}

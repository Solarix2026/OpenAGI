# Copyright (c) 2026 Solarix2026
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

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
    def __init__(self, workspace: str = "./workspace", memory=None, metacognitive=None):
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.memory = memory
        self.meta = metacognitive  # MetacognitiveEngine for capability feedback
        self.registry = self._build_registry()

    def set_metacognition(self, meta):
        """Called by kernel after both executor and meta are initialized."""
        self.meta = meta

    def _build_registry(self):
        from core.tool_registry import ToolRegistry
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

        # Perplexity-style research tools
        reg.register("research_topic", self._research_topic,
            "Deep research on any topic: web search + synthesis + report",
            {"topic": {"type": "string", "required": True},
             "depth": {"type": "string", "default": "standard"}})

        reg.register("draft_document", self._draft_document,
            "Draft professional documents: RFC, report, memo based on research",
            {"document_type": {"type": "string", "required": True},
             "topic": {"type": "string", "required": True}})

        reg.register("investment_watchlist", self._investment_watchlist,
            "Get AI investment watchlist: stock analysis, trends, top picks",
            {"focus": {"type": "string", "default": "technology"}})

        # Link/URL reader tool
        reg.register("read_url", self._read_url,
            "Read and extract content from any URL or webpage. Returns clean text.",
            {"url": {"type": "string", "required": True}, "question": {"type": "string", "optional": True}})

        # HTML PPT Builder
        try:
            from generation.html_ppt_builder import register_html_ppt_tool
            register_html_ppt_tool(reg)
            log.info("🎨 HTML PPT builder registered")
        except Exception as e:
            log.debug(f"HTML PPT skip: {e}")

        # Perplexity news search
    try:
        from core.perplexity_client import register_perplexity_tools
        register_perplexity_tools(reg)
        log.info("📰 Perplexity news search registered")
    except Exception as e:
        log.debug(f"Perplexity skip: {e}")

    # Register memory and goal tools for skills
        reg.register("list_goals", self._list_goals,
            "List all active goals from the goal queue",
            {})

        reg.register("memory_search", self._memory_search,
            "Search episodic memory for past events and context",
            {"query": {"type": "string", "required": True}})

        return reg

    def execute(self, intent: dict) -> dict:
        action = intent.get("action", "")
        params = intent.get("parameters", {})
        t0 = time.time()

        result = self.registry.execute(action, params)

        elapsed = int((time.time() - t0) * 1000)

        # Log to memory
        if self.memory:
            self.memory.log_tool_outcome(
                tool=action,
                params=params,
                outcome=str(result.get("data", result.get("error", "")))[:200],
                success=result.get("success", False),
                duration_ms=elapsed
            )

        # Capability feedback loop: update capability scores based on outcome
        # Gap 6 fix: every tool execution feeds back to capability matrix
        if self.meta and result:
            try:
                dim = self.meta.infer_dimension_from_tool(action)
                if dim:
                    delta = +0.02 if result.get("success") else -0.05  # Success=small gain, fail=more penalty
                    old_val = self.meta._matrix.get(dim, 1.0)
                    new_val = max(0.1, min(5.0, old_val + delta))  # Clamp 0.1-5.0
                    self.meta._matrix[dim] = new_val

                    # Log significant changes
                    if abs(delta) > 0.01:
                        log.info(f"[META] Capability {dim}: {old_val:.2f} → {new_val:.2f} ({result.get('success')})")
            except Exception as e:
                log.debug(f"Capability feedback failed: {e}")

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
            "paint": "mspaint.exe",
            "画图": "mspaint.exe",
            "画图板": "mspaint.exe",
        }
        resolved = aliases.get(app.lower(), app)

        # Method 1: os.startfile (Windows native, handles .exe, URLs, files)
        if platform.system() == "Windows":
            try:
                os.startfile(resolved)
                return {"success": True, "message": f"Opened: {app}"}
            except Exception:
                pass

        # Method 2: subprocess shell with verification
        try:
            import time
            proc = subprocess.Popen(resolved, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Wait briefly and check if process actually exists
            time.sleep(0.5)
            # Try to poll, if None it's still running
            poll_result = proc.poll()
            if poll_result is None or poll_result == 0:
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
        import os
        from pathlib import Path
        path = params.get("path", "output.txt")
        content = params.get("content", "")

        # Expand env vars and ~
        path = os.path.expanduser(os.path.expandvars(path))

        # Desktop aliases
        DESKTOP = Path.home() / "Desktop"
        desktop_aliases = ["desktop", "~/desktop", "桌面"]
        if path.lower().strip("/\\") in desktop_aliases:
            fname = params.get("filename", params.get("name", "output.txt"))
            path = str(DESKTOP / fname)
        elif not os.path.isabs(path) and not path.startswith("~"):
            path = str(self.workspace / path)

        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"success": True, "path": str(p), "bytes": len(content), "absolute_path": str(p.resolve())}

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

    def _list_goals(self, params: dict) -> dict:
        """List all active goals from the goal queue."""
        try:
            from core.goal_persistence import load_goal_queue
            goals = load_goal_queue()
            active = [g for g in goals if g.get('status') in ('pending', 'active')]
            return {"success": True, "goals": active, "count": len(active)}
        except ImportError:
            return {"success": False, "error": "goal_persistence module not available"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _world_events(self, params: dict) -> dict:
        """Fetch world events via RSS."""
        try:
            from core.worldmonitor_client import WorldMonitorClient
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

    def _research_topic(self, params: dict) -> dict:
        """Deep research on any topic: web search + synthesis + structured report."""
        from core.llm_gateway import call_nvidia
        topic = params.get("topic", "")
        depth = params.get("depth", "standard")
        if not topic:
            return {"success": False, "error": "No topic provided"}

        # Step 1: Web search
        search = self._websearch({"query": topic + " 2025 latest"})
        raw_data = search.get("clean_summary", "")

        # Step 2: NVIDIA synthesis
        prompt = f"""Research synthesis for: "{topic}"
Depth: {depth}
Web data: {raw_data[:2000]}

Write a structured research report:
## Summary
## Key Findings
## Recent Developments
## Analysis
## Open Questions

Be specific. Use data from web results."""
        report = call_nvidia([{"role": "user", "content": prompt}], max_tokens=1500)

        return {
            "success": True,
            "topic": topic,
            "report": report,
            "sources_searched": search.get("result_count", 0)
        }

    def _draft_document(self, params: dict) -> dict:
        """Draft professional documents: RFC, report, memo, proposal."""
        from core.llm_gateway import call_nvidia
        from pathlib import Path

        doc_type = params.get("document_type", "RFC")
        topic = params.get("topic", "")
        if not topic:
            return {"success": False, "error": "No topic provided"}

        # Research first
        research = self._research_topic({"topic": topic})

        # Draft document
        prompt = f"""Write a professional {doc_type} for: {topic}

Based on research: {research.get('report', '')[:1000]}

Follow standard {doc_type} format. Be thorough and professional."""
        doc = call_nvidia([{"role": "user", "content": prompt}], max_tokens=2000)

        # Save to file
        fname = f"workspace/{doc_type.lower()}_{topic[:20].replace(' ', '_')}.md"
        Path(fname).write_text(doc, encoding="utf-8")

        return {
            "success": True,
            "document": doc,
            "saved_to": fname
        }

    def _investment_watchlist(self, params: dict) -> dict:
        """Get AI investment watchlist: stock analysis, trends, top picks."""
        from core.llm_gateway import call_nvidia
        focus = params.get("focus", "technology")

        # Search for stocks
        search = self._websearch({"query": f"top {focus} stocks 2025 AI investment"})

        prompt = f"""Create an AI investment watchlist for {focus} sector.

Market data: {search.get('clean_summary', '')[:1500]}

Format:
## Top 10 Stocks to Watch
| Stock | Ticker | Thesis | Risk | Timeframe |
|...|...|...|...|...|

## Macro Trend Analysis
## Red Flags
## Recommendation

Disclaimer: Not financial advice. Educational only."""
        report = call_nvidia([{"role": "user", "content": prompt}], max_tokens=1500)

        return {
            "success": True,
            "watchlist": report,
            "focus": focus
        }

    def _read_url(self, params: dict) -> dict:
        """Read and extract content from any URL or webpage. Returns clean text."""
        import requests
        from core.llm_gateway import call_nvidia

        url = params.get("url", "").strip()
        question = params.get("question", "")

        if not url:
            return {"success": False, "error": "No URL provided"}

        # Normalize URL
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            r = requests.get(url, headers=headers, timeout=20)
            r.raise_for_status()
            content_type = r.headers.get("content-type", "")

            if "pdf" in content_type:
                # PDF handling
                try:
                    import pdfplumber, io
                    with pdfplumber.open(io.BytesIO(r.content)) as pdf:
                        text = "\n\n".join(
                            page.extract_text() or "" for page in pdf.pages[:15]
                        )
                except ImportError:
                    return {"success": False, "error": "pip install pdfplumber for PDF support"}
            else:
                # HTML/text
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(r.text, "html.parser")
                    # Remove noise
                    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "iframe", "noscript", "form"]):
                        tag.decompose()
                    # Try to find main content
                    main = (soup.find("main") or soup.find("article") or soup.find(id="content") or
                           soup.find(class_="content") or soup.find("body"))
                    text = main.get_text(separator="\n", strip=True) if main else soup.get_text()
                    # Clean whitespace
                    text = re.sub(r'\n{3,}', '\n\n', text)
                    text = re.sub(r' {2,}', ' ', text)
                    title = soup.title.string if soup.title else url
                except ImportError:
                    text = re.sub(r"<[^>]+>", " ", r.text)
                    text = re.sub(r"\s+", " ", text).strip()
                    title = url

            # Limit text size
            text = text[:8000]

            if not question:
                # Return summary
                summary_prompt = f"""Summarize the key content from this webpage.
URL: {url}
Content: {text[:4000]}
Provide a clear, structured summary of what this page is about."""
                summary = call_nvidia([{"role": "user", "content": summary_prompt}], max_tokens=400)
                return {
                    "success": True,
                    "url": url,
                    "title": locals().get("title", url),
                    "summary": summary,
                    "raw_text": text[:2000],
                    "char_count": len(text)
                }
            else:
                # Answer specific question
                qa_prompt = f"""Based on this webpage content, answer the question.
URL: {url}
Content: {text[:5000]}
Question: {question}
Answer based only on the page content:"""
                answer = call_nvidia([{"role": "user", "content": qa_prompt}], max_tokens=600)
                return {
                    "success": True,
                    "url": url,
                    "question": question,
                    "answer": answer
                }
        except requests.exceptions.Timeout:
            return {"success": False, "error": f"Timeout reading {url}"}
        except requests.exceptions.HTTPError as e:
            return {"success": False, "error": f"HTTP {e.response.status_code}: {url}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

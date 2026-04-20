# Copyright (c) 2026 ApeironAI
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""
browser_agent.py — Autonomous browser automation

Uses playwright for real browser control + VisionEngine for understanding.

Tools registered:
- browser_navigate(url) — go to URL
- browser_click(selector_or_description) — click element
- browser_fill(field, value) — fill form field
- browser_extract(what) — extract information from current page
- browser_do(task) — HIGH LEVEL: natural language browser task
"""
import logging
import time
import re

log = logging.getLogger("BrowserAgent")


class BrowserAgent:
    def __init__(self, vision_engine=None):
        self.vision = vision_engine
        self._page = None
        self._browser = None
        self._pw = None

    def _ensure_browser(self):
        if self._page is None:
            try:
                from playwright.sync_api import sync_playwright
                self._pw = sync_playwright().start()
                self._browser = self._pw.chromium.launch(headless=False)
                ctx = self._browser.new_context()
                self._page = ctx.new_page()
                log.info("Browser launched")
            except Exception as e:
                log.error(f"Browser launch failed: {e}")
                raise

    def navigate(self, url: str) -> dict:
        self._ensure_browser()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        try:
            self._page.goto(url, timeout=15000)
            title = self._page.title()
            return {"success": True, "url": url, "title": title}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def extract_content(self, what: str = "all text") -> dict:
        """Extract information from current page using NVIDIA."""
        if not self._page:
            return {"success": False, "error": "No page open"}
        try:
            # Get page text
            text = self._page.inner_text("body")[:3000]
            url = self._page.url
            from core.llm_gateway import call_nvidia
            prompt = f"""Extract from this webpage: {what}

URL: {url}
Content: {text}

Return the extracted information clearly."""
            result = call_nvidia([{"role": "user", "content": prompt}], max_tokens=600)
            return {"success": True, "extracted": result, "url": url}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def click_element(self, description: str) -> dict:
        """Click an element by text or aria description."""
        if not self._page:
            return {"success": False, "error": "No page open"}
        try:
            # Try various selectors
            for selector in [
                f"text={description}",
                f"[aria-label='{description}']",
                f"button:has-text('{description}')"
            ]:
                try:
                    self._page.click(selector, timeout=3000)
                    return {"success": True, "clicked": description}
                except Exception:
                    continue
            return {"success": False, "error": f"Element not found: {description}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def fill_field(self, selector: str, value: str) -> dict:
        """Fill a form field."""
        if not self._page:
            return {"success": False, "error": "No page open"}
        try:
            self._page.fill(selector, value)
            return {"success": True, "filled": selector}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def do_task(self, task: str) -> dict:
        """HIGH LEVEL: browser task in natural language."""
        self._ensure_browser()
        from core.llm_gateway import call_nvidia
        import json

        prompt = f"""Plan browser automation for: "{task}"

Current URL: {self._page.url if self._page else 'none'}

Return ordered steps as JSON:
{{"steps": [{{"action":"navigate|click|fill|extract|wait", "value":"...", "reason":"..."}}]}}"""
        raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=400, fast=True)
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        plan = json.loads(m.group(0)) if m else {"steps": []}

        results = []
        for step in plan.get("steps", [])[:10]:
            act = step.get("action", "")
            val = step.get("value", "")
            if act == "navigate":
                r = self.navigate(val)
            elif act == "click":
                r = self.click_element(val)
            elif act == "fill":
                parts = val.split("=", 1)
                r = self.fill_field(parts[0], parts[1] if len(parts) > 1 else "")
            elif act == "extract":
                r = self.extract_content(val)
            elif act == "wait":
                time.sleep(float(val or 1))
                r = {"success": True}
            else:
                r = {"success": False, "error": f"Unknown: {act}"}
            results.append({"action": act, "result": r})
            if not r.get("success"):
                break

        return {"success": all(r["result"].get("success") for r in results), "steps": results}

    def close(self):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()

    def register_as_tool(self, registry):
        agent = self

        def browser_do(params):
            return agent.do_task(params.get("task", ""))

        def browser_nav(params):
            return agent.navigate(params.get("url", ""))

        def browser_extract(params):
            return agent.extract_content(params.get("what", "main content"))

        registry.register(
            "browser_do",
            browser_do,
            "Automate browser with natural language: fill forms, click buttons, extract data, login",
            {"task": {"type": "string", "required": True}},
            "browser"
        )
        registry.register(
            "browser_extract",
            browser_extract,
            "Extract specific information from current browser page",
            {"what": {"type": "string", "default": "all content"}},
            "browser"
        )

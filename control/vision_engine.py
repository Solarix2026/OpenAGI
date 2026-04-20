# Copyright (c) 2026 ApeironAI
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""
vision_engine.py — Screen and image understanding via NVIDIA NIM

Uses NVIDIA's vision models via OpenAI-compatible API.
Primary model: meta/llama-3.2-90b-vision-instruct

Capabilities:
- analyze_screenshot(): describe current screen state
- find_element(description): locate UI element, return coordinates
- read_text_from_image(): OCR any image
- understand_layout(): parse screen regions for automation
- validate_action_result(): confirm action succeeded visually
"""
import base64
import logging
import os
import re
from pathlib import Path

log = logging.getLogger("Vision")
VISION_MODEL = os.getenv("NVIDIA_VISION_MODEL", "meta/llama-3.2-90b-vision-instruct")


class VisionEngine:
    def __init__(self):
        try:
            from openai import OpenAI
            self._client = OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=os.getenv("NVIDIA_API_KEY")
            )
        except Exception as e:
            log.error(f"Vision client init failed: {e}")
            self._client = None

    def _encode_image(self, path: str) -> str:
        return base64.b64encode(Path(path).read_bytes()).decode("utf-8")

    def _call_vision(self, image_path: str, prompt: str, max_tokens=500) -> str:
        """Use dedicated vision function instead of generic call_nvidia."""
        from core.llm_gateway import call_vision
        return call_vision(
            [{"role": "user", "content": prompt}],
            image_path=image_path,
            max_tokens=max_tokens
        )
                temperature=0.1
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            log.error(f"Vision call failed: {e}")
            return ""

    def analyze_screenshot(self, path: str) -> dict:
        """Describe current screen: what app, what's visible, what's interactive."""
        desc = self._call_vision(path, "Describe this screenshot: what application is open, what content is visible, " "what UI elements are present (buttons, forms, menus). Be specific.", 400)
        return {"success": True, "description": desc, "path": path}

    def find_element(self, path: str, description: str) -> dict:
        """Locate UI element. Returns estimated coordinates as fractions (0-1)."""
        resp = self._call_vision(path, f"Find '{description}' in this screenshot. " "Return JSON: {{\"found\": true/false, \"x_fraction\": 0.5, \"y_fraction\": 0.3, " "\"description\": \"what you found\"}}", 200)
        import json
        m = re.search(r'\{.*\}', resp, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            return {"success": data.get("found", False), **data}
        return {"success": False, "found": False}

    def read_text_from_image(self, path: str) -> str:
        """Extract all visible text from an image (OCR)."""
        return self._call_vision(path, "Read and return all visible text in this image exactly as written. " "Preserve formatting if possible.", 600)

    def validate_action_result(self, before_path: str, after_path: str, expected: str) -> dict:
        """Compare before/after screenshots to verify action succeeded."""
        before_desc = self.analyze_screenshot(before_path)["description"]
        after_desc = self.analyze_screenshot(after_path)["description"]
        from core.llm_gateway import call_nvidia

        prompt = f"""Did this action succeed: "{expected}"?

Before: {before_desc[:200]}
After: {after_desc[:200]}

Return JSON: {{"success": true/false, "evidence": "what changed", "confidence": 0.0-1.0}}"""
        raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=150, fast=True)
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        import json
        return json.loads(m.group(0)) if m else {"success": False}

    def register_as_tool(self, registry):
        def vision_analyze(params: dict) -> dict:
            path = params.get("path", "")
            task = params.get("task", "analyze")
            if not path:
                # Auto-screenshot
                try:
                    import pyautogui
                    import time
                    path = f"./workspace/vision_{int(time.time())}.png"
                    pyautogui.screenshot(path)
                except Exception as e:
                    return {"success": False, "error": f"Screenshot failed: {e}"}

            if task == "find":
                return self.find_element(path, params.get("element", ""))
            elif task == "ocr":
                text = self.read_text_from_image(path)
                return {"success": True, "text": text}
            else:
                return self.analyze_screenshot(path)

        registry.register(
            name="vision_analyze",
            func=vision_analyze,
            description="Analyze screen or image with NVIDIA vision AI: describe, find UI elements, read text, validate actions",
            parameters={"path": {"type": "string", "optional": True}, "task": {"type": "string", "default": "analyze"}},
            category="computer_control"
        )

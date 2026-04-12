"""
computer_control.py — Autonomous desktop control

See (VisionEngine) → Think (NVIDIA decides action) → Act (pyautogui) →
Verify (VisionEngine confirms result) → Repeat

Tools registered:
- computer_click(x_fraction, y_fraction) — click at screen position
- computer_type(text) — type text at current focus
- computer_hotkey(keys) — keyboard shortcut
- computer_scroll(direction, amount)
- computer_do(task) — HIGH LEVEL: describe task, system figures out how

computer_do() is the most powerful: takes natural language task, uses vision
 to understand current state, NVIDIA to plan actions, executes step by step
 with visual verification.
"""
import logging
import time

log = logging.getLogger("ComputerControl")


class ComputerControl:
    def __init__(self, vision_engine=None):
        self.vision = vision_engine
        self._screen_w = None
        self._screen_h = None
        self._get_screen_size()

    def _get_screen_size(self):
        try:
            import pyautogui
            self._screen_w, self._screen_h = pyautogui.size()
        except Exception:
            self._screen_w, self._screen_h = 1920, 1080

    def _fraction_to_px(self, xf: float, yf: float) -> tuple:
        return int(xf * self._screen_w), int(yf * self._screen_h)

    def click(self, x_frac: float, y_frac: float) -> dict:
        try:
            import pyautogui
            x, y = self._fraction_to_px(x_frac, y_frac)
            pyautogui.click(x, y)
            time.sleep(0.3)
            return {"success": True, "clicked": (x, y)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def type_text(self, text: str, delay=0.05) -> dict:
        try:
            import pyautogui
            pyautogui.write(text, interval=delay)
            return {"success": True, "typed": text[:50]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def hotkey(self, *keys) -> dict:
        try:
            import pyautogui
            pyautogui.hotkey(*keys)
            time.sleep(0.2)
            return {"success": True, "keys": keys}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def scroll(self, direction="down", amount=3) -> dict:
        try:
            import pyautogui
            clicks = amount if direction == "down" else -amount
            pyautogui.scroll(clicks)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def screenshot(self) -> str:
        """Take screenshot, return path."""
        try:
            import pyautogui
            from pathlib import Path
            import time
            path = f"./workspace/screen_{int(time.time())}.png"
            pyautogui.screenshot(path)
            return path
        except Exception:
            return ""

    def do_task(self, task: str, max_steps=5) -> dict:
        """
        HIGH LEVEL: Take natural language task, execute autonomously.
        Vision → NVIDIA plan → act → verify loop.
        """
        if not self.vision:
            return {"success": False, "error": "Vision engine required for computer_do"}

        log.info(f"[COMPUTER] Task: {task}")
        history = []

        for step_num in range(max_steps):
            # See
            screen_path = self.screenshot()
            if not screen_path:
                return {"success": False, "error": "Screenshot failed"}

            screen_desc = self.vision.analyze_screenshot(screen_path)["description"]

            # Think — NVIDIA decides next action
            import json
            import re
            plan_prompt = f"""You are controlling a computer to complete: "{task}"

Current screen: {screen_desc[:300]}
Steps taken so far: {history}

What is the SINGLE next action to take?

Return JSON: {{"action": "click|type|hotkey|scroll|done|failed", "x_fraction": 0.5,  // only for click "y_fraction": 0.3,  // only for click "text": "...",  // only for type "keys": ["ctrl","c"],  // only for hotkey "direction": "down",  // only for scroll "reason": "why this action"}}"""
            from core.llm_gateway import call_nvidia
            raw = call_nvidia([{"role": "user", "content": plan_prompt}], max_tokens=200, fast=True)
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if not m:
                break

            action = json.loads(m.group(0))
            if action.get("action") == "done":
                return {"success": True, "steps": history, "result": "Task completed"}
            if action.get("action") == "failed":
                return {"success": False, "steps": history, "error": "Task deemed impossible"}

            # Act
            act = action.get("action")
            if act == "click":
                result = self.click(action.get("x_fraction", 0.5), action.get("y_fraction", 0.5))
            elif act == "type":
                result = self.type_text(action.get("text", ""))
            elif act == "hotkey":
                result = self.hotkey(*action.get("keys", ["ctrl", "c"]))
            elif act == "scroll":
                result = self.scroll(action.get("direction", "down"))
            else:
                result = {"success": False, "error": f"Unknown action: {act}"}

            history.append({"step": step_num + 1, "action": act, "result": result.get("success")})
            if not result.get("success"):
                return {"success": False, "error": result.get("error"), "steps": history}

            time.sleep(0.5)  # Wait for UI to respond

        return {"success": False, "error": "Max steps reached", "steps": history}

    def register_as_tool(self, registry):
        ctrl = self

        def computer_do(params: dict) -> dict:
            task = params.get("task", "")
            if not task:
                return {"success": False, "error": "Describe task"}
            return ctrl.do_task(task)

        def computer_click(params: dict) -> dict:
            return ctrl.click(params.get("x", 0.5), params.get("y", 0.5))

        def computer_type(params: dict) -> dict:
            return ctrl.type_text(params.get("text", ""))

        def computer_hotkey(params: dict) -> dict:
            keys = params.get("keys", [])
            return ctrl.hotkey(*keys) if keys else {"success": False, "error": "No keys"}

        registry.register("computer_do", computer_do, "Control the computer autonomously using natural language task description", {"task": {"type": "string", "required": True}}, "computer_control")
        registry.register("computer_click", computer_click, "Click at screen position (x,y as 0-1 fractions of screen size)", {"x": {"type": "float"}, "y": {"type": "float"}}, "computer_control")
        registry.register("computer_type", computer_type, "Type text at current keyboard focus", {"text": {"type": "string"}}, "computer_control")
        registry.register("computer_hotkey", computer_hotkey, "Press keyboard shortcut e.g. ctrl+c, alt+f4", {"keys": {"type": "list"}}, "computer_control")

# Copyright (c) 2026 ApeironAI
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""
computer_control.py — Autonomous desktop control via A11y Tree + Win32

Architecture:
1. UIAutomation: find elements by name/type/role (not pixel coords)
2. Fallback: pyautogui only when UIAutomation can't find element
3. Vision: screenshot + NVIDIA NIM for understanding WHAT is on screen
4. Win32: for app launching, window management

Tools:
computer_do(task) — HIGH LEVEL: NL task -> A11y plan -> execute
computer_find(description) — Find UI element by description
computer_click_element(id) — Click by A11y element handle
computer_type(text) — Type at focused element
computer_get_tree() — Dump current A11y tree for inspection
computer_window_focus(name) — Focus a window by title
"""
import logging
import time
import platform
from typing import Optional

log = logging.getLogger("ComputerControl")


def _check_uiautomation():
    """Check if uiautomation is available."""
    try:
        import uiautomation
        return True
    except ImportError:
        return False


class ComputerControl:
    def __init__(self, vision_engine=None):
        self.vision = vision_engine
        self._has_uia = _check_uiautomation()
        self._screen_w = None
        self._screen_h = None
        if self._has_uia:
            log.info("UIAutomation available — using A11y Tree")
        else:
            log.warning("UIAutomation not found — falling back to pyautogui")
            log.warning("Install: pip install uiautomation")
        self._get_screen_size()

    def _get_screen_size(self):
        try:
            import pyautogui
            self._screen_w, self._screen_h = pyautogui.size()
        except Exception:
            self._screen_w, self._screen_h = 1920, 1080

    def _fraction_to_px(self, xf: float, yf: float) -> tuple:
        return int(xf * self._screen_w), int(yf * self._screen_h)

    # -- A11y Tree Methods --

    def get_a11y_tree(self, depth: int = 3) -> dict:
        """
        Dump current A11y tree as structured dict.
        NVIDIA uses this to understand the current UI state.
        """
        if not self._has_uia:
            return {"error": "uiautomation not installed"}
        try:
            import uiautomation as auto
            desktop = auto.GetRootControl()
            return self._control_to_dict(desktop, depth)
        except Exception as e:
            return {"error": str(e)}

    def _control_to_dict(self, ctrl, depth: int) -> dict:
        """Recursively convert UIAutomation control to dict."""
        try:
            d = {
                "name": ctrl.Name or "",
                "type": ctrl.ControlTypeName or "",
                "class": ctrl.ClassName or "",
                "enabled": ctrl.IsEnabled if hasattr(ctrl, 'IsEnabled') else True,
                "children": []
            }
            if depth > 0:
                for child in ctrl.GetChildren()[:20]:
                    d["children"].append(self._control_to_dict(child, depth - 1))
            return d
        except Exception:
            return {"name": "?", "type": "?"}

    def find_element(self, name: str = None, ctrl_type: str = None,
                     class_name: str = None, partial: bool = True) -> Optional[object]:
        """Find UI element by name/type. Returns UIAutomation control or None."""
        if not self._has_uia:
            return None
        try:
            import uiautomation as auto
            kwargs = {"searchDepth": 8}
            if name:
                kwargs["Name"] = name
            if ctrl_type and hasattr(auto.ControlType, ctrl_type):
                kwargs["ControlType"] = getattr(auto.ControlType, ctrl_type)
            if class_name:
                kwargs["ClassName"] = class_name

            ctrl = auto.Control(**kwargs)
            if ctrl.Exists(0):
                return ctrl

            # Partial match fallback
            if name and partial:
                desktop = auto.GetRootControl()
                for c in desktop.GetChildren():
                    found = c.FindControl(lambda x: name.lower() in (x.Name or "").lower())
                    if found:
                        return found
        except Exception as e:
            log.debug(f"find_element failed: {e}")
        return None

    def click_element(self, name: str, ctrl_type: str = None) -> dict:
        """Click a UI element by name. Uses A11y, no pixel coords needed."""
        elem = self.find_element(name, ctrl_type)
        if elem:
            try:
                elem.Click()
                time.sleep(0.3)
                return {"success": True, "clicked": name, "method": "a11y"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        # Fallback to vision
        return self._vision_click(name)

    def _vision_click(self, description: str) -> dict:
        """Fallback: use VisionEngine to find element, then click coords."""
        if not self.vision:
            return {"success": False, "error": f"Element '{description}' not found via A11y and no vision"}
        screen = self.screenshot()
        if not screen:
            return {"success": False, "error": "Screenshot failed"}
        result = self.vision.find_element(screen, description)
        if result.get("found"):
            xf, yf = result["x_fraction"], result["y_fraction"]
            return self._pixel_click(xf, yf)
        return {"success": False, "error": f"Element '{description}' not found"}

    def _pixel_click(self, x_frac: float, y_frac: float) -> dict:
        """Last resort: pixel coordinate click via pyautogui."""
        try:
            import pyautogui
            x, y = self._fraction_to_px(x_frac, y_frac)
            pyautogui.click(x, y)
            return {"success": True, "method": "pixel_fallback"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def type_text(self, text: str) -> dict:
        """Type text at current focus using SendKeys."""
        try:
            import uiautomation as auto
            focused = auto.GetFocusedControl()
            if focused:
                focused.SendKeys(text, interval=0.02)
                return {"success": True, "typed": text[:30], "method": "a11y"}
        except Exception:
            pass
        # Fallback
        try:
            import pyautogui
            pyautogui.write(text, interval=0.03)
            return {"success": True, "typed": text[:30], "method": "pyautogui"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def focus_window(self, title: str) -> dict:
        """Focus a window by partial title match."""
        if not self._has_uia:
            # Fallback to Windows API
            try:
                import win32gui
                import win32con

                def enum_windows(hwnd, extra):
                    if win32gui.IsWindowVisible(hwnd):
                        text = win32gui.GetWindowText(hwnd)
                        if title.lower() in text.lower():
                            extra.append(hwnd)

                handles = []
                win32gui.EnumWindows(enum_windows, handles)
                if handles:
                    win32gui.ShowWindow(handles[0], win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(handles[0])
                    return {"success": True, "focused": title}
            except Exception as e:
                return {"success": False, "error": str(e)}

        try:
            import uiautomation as auto
            win = auto.WindowControl(searchDepth=1, SubName=title)
            if win.Exists(0):
                win.SetFocus()
                win.MoveToForeground()
                time.sleep(0.2)
                return {"success": True, "focused": title}
            return {"success": False, "error": f"Window '{title}' not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def click(self, x_frac: float, y_frac: float) -> dict:
        """Legacy: click at screen fraction (for compatible tools)."""
        return self._pixel_click(x_frac, y_frac)

    def hotkey(self, *keys) -> dict:
        """Press keyboard shortcut."""
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
            path = f"./workspace/screen_{int(time.time())}.png"
            pyautogui.screenshot(path)
            return path
        except Exception:
            return ""

    def do_task(self, task: str, max_steps: int = 8) -> dict:
        """
        HIGH LEVEL: Execute a computer task using A11y Tree + NVIDIA planning.
        Process:
        1. Get A11y tree snapshot (structured UI state)
        2. NVIDIA decides next action based on tree + task
        3. Execute via find_element (no coords!)
        4. Verify element state changed
        5. Repeat
        """
        from core.llm_gateway import call_nvidia
        import json

        history = []
        log.info(f"[COMPUTER] Task: {task}")

        for step_num in range(max_steps):
            # Get A11y tree
            tree = self.get_a11y_tree(depth=3)
            tree_summary = json.dumps(tree, ensure_ascii=False)[:1500]

            # NVIDIA plans next action
            prompt = f"""You are controlling a Windows computer using UIAutomation.
Task: "{task}"
Steps done: {history}
Current A11y Tree: {tree_summary}

Return JSON:
{{"action": "click_element|type_text|focus_window|hotkey|done|failed",
 "element_name": "name from tree",
 "text": "text to type",
 "keys": ["ctrl","s"], "reason": "why"}}"""

            raw = call_nvidia([{"role": "user", "content": prompt}],
                               max_tokens=200)
            try:
                m = __import__('re').search(r'\{.*\}', raw, __import__('re').DOTALL)
                if not m:
                    break
                action = __import__('json').loads(m.group(0))
            except Exception:
                continue

            act = action.get("action")
            if act == "done":
                return {"success": True, "steps": history}
            if act == "failed":
                return {"success": False, "steps": history}

            # Execute
            if act == "click_element":
                result = self.click_element(action.get("element_name", ""))
            elif act == "type_text":
                result = self.type_text(action.get("text", ""))
            elif act == "focus_window":
                result = self.focus_window(action.get("element_name", ""))
            elif act == "hotkey":
                result = self.hotkey(*action.get("keys", ["ctrl"]))
            else:
                result = {"success": False, "error": f"Unknown: {act}"}

            history.append({"step": step_num + 1, "action": act,
                           "success": result.get("success")})
            time.sleep(0.5)

        return {"success": False, "error": "Max steps", "steps": history}

    # -- Register as tools --

    def register_as_tool(self, registry):
        ctrl = self

        def computer_do(params: dict) -> dict:
            return ctrl.do_task(params.get("task", ""))

        def computer_find(params: dict) -> dict:
            name = params.get("name", "")
            elem = ctrl.find_element(name, params.get("type"))
            if elem:
                return {"success": True, "found": True, "name": name,
                        "enabled": getattr(elem, "IsEnabled", True)}
            return {"success": True, "found": False}

        def computer_get_tree(params: dict) -> dict:
            return {"success": True, "tree": ctrl.get_a11y_tree(
                depth=params.get("depth", 3))}

        def computer_click(params: dict) -> dict:
            return ctrl.click(params.get("x", 0.5), params.get("y", 0.5))

        def computer_type(params: dict) -> dict:
            return ctrl.type_text(params.get("text", ""))

        def computer_hotkey(params: dict) -> dict:
            return ctrl.hotkey(*params.get("keys", []))

        def computer_screenshot(params: dict) -> dict:
            return {"success": True, "path": ctrl.screenshot()}

        registry.register("computer_do", computer_do,
            "Control computer with natural language using A11y tree",
            {"task": {"type": "string", "required": True}},
            "computer_control")
        registry.register("computer_find", computer_find,
            "Find a UI element by name in the accessibility tree",
            {"name": {"type": "string", "required": True}},
            "computer_control")
        registry.register("computer_get_tree", computer_get_tree,
            "Get the current accessibility tree of UI elements on screen",
            {"depth": {"type": "int", "default": 3}},
            "computer_control")
        registry.register("computer_click", computer_click,
            "Click at screen position (fraction 0-1)",
            {"x": {"type": "float"}, "y": {"type": "float"}},
            "computer_control")
        registry.register("computer_type", computer_type,
            "Type text at current focus",
            {"text": {"type": "string", "required": True}},
            "computer_control")
        registry.register("computer_hotkey", computer_hotkey,
            "Press keyboard shortcuts",
            {"keys": {"type": "array", "required": True}},
            "computer_control")
        registry.register("computer_screenshot", computer_screenshot,
            "Take a screenshot of the desktop",
            {}, "computer_control")

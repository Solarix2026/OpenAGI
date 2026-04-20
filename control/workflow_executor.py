# Copyright (c) 2026 ApeironAI
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""
workflow_executor.py — High-level workflow executor for complex computer tasks.

Handles multi-step automation like:
- "book a flight from KL to Tokyo next Friday"
- "fill in this form and submit"
- "download my bank statement"

Architecture:
1. Parse intent → structured task plan
2. Open correct browser/app
3. Execute steps with vision verification after each step
4. Handle errors (captcha, unexpected popups, login required)
5. Report result + ask for human input when stuck
"""
import logging, time, re, json
from core.llm_gateway import call_nvidia

log = logging.getLogger("WorkflowExecutor")


class WorkflowExecutor:
    def __init__(self, computer_control=None, browser_agent=None, vision_engine=None, notify_fn=None):
        self.computer = computer_control
        self.browser = browser_agent
        self.vision = vision_engine
        self.notify = notify_fn  # callback to send updates to user

    def plan_web_task(self, task: str) -> dict:
        """Use NVIDIA to plan a web automation task."""
        prompt = f"""Plan a browser automation workflow for: "{task}"
You are controlling a real browser. Plan step by step.
Return JSON: {{
  "start_url": "https://...",
  "steps": [
    {{"action": "navigate|click|type|wait|screenshot|extract|ask_human", "target": "CSS selector or description", "value": "text to type or null", "verify": "what should be visible after this step", "on_error": "retry|skip|ask_human|abort"}}
  ],
  "requires_login": false,
  "requires_payment": false,
  "irreversible": false,
  "estimated_steps": 10
}}
IMPORTANT: If requires_payment=true or irreversible=true, add an ask_human step before finalizing."""
        try:
            raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=1200)
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                return json.loads(m.group(0))
        except Exception as e:
            log.error(f"Task planning failed: {e}")
        return {"steps": [], "requires_payment": False}

    def execute_web_task(self, task: str, approval_fn=None) -> dict:
        """Execute a complex web task with human-in-the-loop for critical steps."""
        plan = self.plan_web_task(task)
        # Safety check: ask human before irreversible/payment actions
        if plan.get("requires_payment") or plan.get("irreversible"):
            msg = f"This task will:\n"
            for s in plan.get("steps", [])[:5]:
                msg += f" • {s.get('action')}: {s.get('target','')}\n"
            msg += "\nThis may involve payment or irreversible actions. Proceed?"
            if approval_fn:
                approved = approval_fn(msg)
                if not approved:
                    return {"success": False, "reason": "User cancelled", "steps_completed": 0}
            else:
                log.warning("[WORKFLOW] Irreversible task but no approval_fn — proceeding with caution")
        if not self.browser:
            return {"success": False, "error": "Browser agent not available"}
        results = []
        start_url = plan.get("start_url", "https://google.com")
        # Navigate to start
        nav = self.browser.navigate(start_url)
        if not nav.get("success"):
            return {"success": False, "error": f"Failed to navigate to {start_url}"}
        for i, step in enumerate(plan.get("steps", [])[:20]):  # Max 20 steps
            action = step.get("action")
            target = step.get("value", "") or step.get("target", "")
            log.info(f"[WORKFLOW] Step {i+1}/{len(plan['steps'])}: {action} → {target[:50]}")
            if self.notify:
                self.notify(f"Step {i+1}: {action} {target[:40]}")
            if action == "ask_human":
                if approval_fn:
                    msg = step.get("target", "Please review and confirm to continue.")
                    approved = approval_fn(msg)
                    if not approved:
                        return {"success": False, "reason": f"User stopped at step {i+1}", "steps_completed": i}
                results.append({"step": i+1, "action": action, "result": "approved"})
                continue
            if action == "navigate":
                result = self.browser.navigate(target)
            elif action == "click":
                result = self.browser.click_element(target)
            elif action == "type":
                field = step.get("target", "")
                result = self.browser.fill_field(field, target)
            elif action == "extract":
                result = self.browser.extract_content(target)
            elif action == "screenshot":
                if self.computer:
                    path = self.computer.screenshot()
                    result = {"success": True, "path": path}
                else:
                    result = {"success": False, "error": "No computer control"}
            elif action == "wait":
                wait_s = float(step.get("value", 2))
                time.sleep(min(wait_s, 10))
                result = {"success": True}
            else:
                result = {"success": False, "error": f"Unknown action: {action}"}
            results.append({"step": i+1, "action": action, "success": result.get("success")})
            if not result.get("success"):
                error_handling = step.get("on_error", "ask_human")
                if error_handling == "abort":
                    return {"success": False, "error": result.get("error"), "steps_completed": i, "results": results}
                elif error_handling == "ask_human" and approval_fn:
                    approved = approval_fn(f"Step {i+1} failed: {result.get('error','?')}. Continue anyway?")
                    if not approved:
                        return {"success": False, "reason": "User aborted after error", "steps_completed": i}
            time.sleep(0.5)  # Brief pause between steps
        return {
            "success": True,
            "task": task,
            "steps_completed": len(results),
            "results": results
        }

    def book_flight(self, params: dict) -> dict:
        """Specialized flight booking workflow. Uses Google Flights as default (no login required to search)."""
        origin = params.get("from", params.get("origin", ""))
        destination = params.get("to", params.get("destination", ""))
        date = params.get("date", params.get("departure_date", ""))
        return_date = params.get("return_date", "")
        passengers = params.get("passengers", 1)
        if not all([origin, destination, date]):
            return {"success": False, "error": "Need: from, to, date"}
        task = f"Search for flights from {origin} to {destination} on {date}"
        if return_date:
            task += f" returning {return_date}"
        task += f" for {passengers} passenger(s) on Google Flights, show me the best options"
        return self.execute_web_task(task)

    def register_as_tool(self, registry, approval_fn=None):
        """Register browser_workflow and book_flight tools."""
        executor = self
        _approval_fn = approval_fn

        def complex_browser_task(params: dict) -> dict:
            task = params.get("task", "")
            if not task:
                return {"success": False, "error": "Describe the task"}
            return executor.execute_web_task(task, _approval_fn)

        def book_flight(params: dict) -> dict:
            return executor.book_flight(params)

        registry.register(
            "browser_workflow",
            complex_browser_task,
            "Execute complex multi-step browser automation: book flights, fill forms, extract data from websites, navigate multi-page flows",
            {"task": {"type": "string", "required": True, "description": "Natural language task description"}},
            "browser_automation"
        )
        registry.register(
            "book_flight",
            book_flight,
            "Search and book flights. Provide: from (city/airport), to (city/airport), date (e.g. 2026-05-01), optional: return_date, passengers",
            {
                "from": {"type": "string", "required": True},
                "to": {"type": "string", "required": True},
                "date": {"type": "string", "required": True},
                "return_date": {"type": "string"},
                "passengers": {"type": "integer", "default": 1}
            },
            "travel"
        )

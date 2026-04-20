# Copyright (c) 2026 HackerTMJ
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""
cron_scheduler.py — Persistent cron-style task scheduler

Schedules survive restarts (stored in workspace/scheduled_tasks.json).
Runs in background thread, checks every 60 seconds.
Supports: cron expressions, natural language schedules.

Natural language → cron mapping (via NVIDIA):
"every morning at 8am" → "0 8 * * *"
"every monday at 9am" → "0 9 * * 1"
"every 30 minutes" → "*/30 * * * *"
"""
import json
import threading
import time
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Callable

log = logging.getLogger("CronScheduler")
TASKS_PATH = Path("./workspace/scheduled_tasks.json")


class CronScheduler:
    def __init__(self, kernel_ref):
        self.kernel = kernel_ref
        self._tasks = self._load()
        self._stop = threading.Event()
        self._thread = None

    def _load(self) -> list:
        try:
            return json.loads(TASKS_PATH.read_text())
        except Exception as e:
            log.debug(f"Could not load scheduled tasks: {e}")
            return []

    def _save(self):
        TASKS_PATH.parent.mkdir(parents=True, exist_ok=True)
        TASKS_PATH.write_text(json.dumps(self._tasks, indent=2))

    def add_task(self, description: str, cron: str = None, natural: str = None) -> dict:
        """Add a scheduled task. Either cron expr or natural language."""
        if natural and not cron:
            cron = self._natural_to_cron(natural)
        task = {
            "id": f"cron_{int(time.time())}",
            "description": description,
            "cron": cron,
            "natural": natural or "",
            "enabled": True,
            "last_run": None,
            "run_count": 0
        }
        self._tasks.append(task)
        self._save()
        log.info(f"[CRON] Added: {description} @ {cron}")
        return task

    def _natural_to_cron(self, text: str) -> str:
        """Convert natural language to cron using regex patterns first, then NVIDIA fallback."""
        import re

        # Fast regex patterns
        text_lower = text.lower().strip()

        # "every day at X" or "every day at X:Y am/pm"
        match = re.search(r"every day at (\d+)(?::(\d+))?\s*(am|pm)?", text_lower)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            ampm = match.group(3)
            if ampm == "pm" and hour != 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
            return f"{minute} {hour} * * *"

        # "every morning"
        if "every morning" in text_lower:
            return "0 8 * * *"

        # "every evening"
        if "every evening" in text_lower:
            return "0 18 * * *"

        # "every hour"
        if "every hour" in text_lower:
            return "0 * * * *"

        # "every N minutes"
        match = re.search(r"every (\d+) minutes?", text_lower)
        if match:
            return f"*/{match.group(1)} * * * *"

        # "every monday at X am/pm"
        days = {"monday": "1", "tuesday": "2", "wednesday": "3", "thursday": "4",
                "friday": "5", "saturday": "6", "sunday": "0"}
        for day_name, day_num in days.items():
            match = re.search(rf"every {day_name} at (\d+)(?::(\d+))?\s*(am|pm)?", text_lower)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2)) if match.group(2) else 0
                ampm = match.group(3)
                if ampm == "pm" and hour != 12:
                    hour += 12
                elif ampm == "am" and hour == 12:
                    hour = 0
                return f"{minute} {hour} * * {day_num}"

        # "every month on day N"
        match = re.search(r"every month on day (\d+)", text_lower)
        if match:
            day = match.group(1)
            return f"0 9 {day} * *"  # Default 9 AM

        # LLM fallback for complex expressions
        try:
            from core.llm_gateway import call_nvidia
            prompt = f"""Convert to cron expression: "{text}"
Return ONLY the cron string (5 fields), nothing else.
Examples:
"every day at 8am" → 0 8 * * *
"every monday at 9am" → 0 9 * * 1
"every 30 minutes" → */30 * * * *

Your response:"""
            raw = call_nvidia([{"role":"user","content":prompt}], max_tokens=20, fast=True)
            cron = raw.strip().split('\n')[0]
            if len(cron.split()) == 5:
                return cron
        except Exception as e:
            log.debug(f"NVIDIA cron conversion failed: {e}")

        # Fallback: 9am daily
        return "0 9 * * *"

    def _cron_matches(self, cron: str, now: datetime) -> bool:
        """Check if cron expression matches current time."""
        try:
            parts = cron.split()
            if len(parts) != 5:
                return False
            minute, hour, dom, month, dow = parts

            def matches(field, value):
                if field == '*':
                    return True
                if field.startswith('*/'):
                    return value % int(field[2:]) == 0
                # Handle ranges like "1-5"
                if '-' in str(field):
                    start, end = map(int, str(field).split('-'))
                    return start <= value <= end
                # Handle lists like "1,3,5"
                if ',' in str(field):
                    return value in map(int, str(field).split(','))
                return int(field) == value

            return (matches(minute, now.minute) and
                    matches(hour, now.hour) and
                    matches(dom, now.day) and
                    matches(month, now.month) and
                    matches(dow, now.weekday()))
        except Exception as e:
            log.debug(f"Cron matching error: {e}")
            return False

    def _run_loop(self):
        log.info("[CRON] Scheduler started")
        while not self._stop.is_set():
            now = datetime.now()
            for task in self._tasks:
                if not task.get("enabled"):
                    continue

                last = task.get("last_run", "")
                last_minute = last[:16] if last else ""
                this_minute = now.strftime("%Y-%m-%d %H:%M")

                if last_minute != this_minute and self._cron_matches(task["cron"], now):
                    log.info(f"[CRON] Running: {task['description'][:60]}")
                    try:
                        result = self.kernel.process(task["description"])
                        task["last_run"] = now.isoformat()
                        task["run_count"] = task.get("run_count", 0) + 1
                        self._save()

                        # Notify via Telegram + WebUI
                        try:
                            from core.llm_gateway import send_telegram_alert
                            send_telegram_alert(
                                f"⏰ Scheduled task ran:\n{result[:400]}"
                            )
                            if hasattr(self.kernel, '_webui_push') and self.kernel._webui_push:
                                self.kernel._webui_push(
                                    f"⏰ Scheduled: {task['description'][:50]}...\n{result[:300]}"
                                )
                        except Exception as e:
                            log.debug(f"Notification error: {e}")
                    except Exception as e:
                        log.error(f"[CRON] Task failed: {e}")

            self._stop.wait(60)  # Check every minute

    def start(self):
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="CronScheduler"
        )
        self._thread.start()

    def stop(self):
        self._stop.set()

    def schedule_with_reminder(self, description: str, cron: str = None, natural: str = None, notify_completion: bool = True) -> dict:
        """Schedule a task with optional completion notification."""
        task = self.add_task(description, cron=cron, natural=natural)
        task["notify_completion"] = notify_completion
        task["scheduled"] = datetime.now().isoformat()
        self._update_task(task)
        return task

    def _update_task(self, updated_task: dict):
        """Update a task in storage."""
        for i, t in enumerate(self._tasks):
            if t.get("id") == updated_task.get("id"):
                self._tasks[i] = updated_task
                self._save()
                return True
        return False

    def _broadcast_task_complete(self, task: dict, result: str):
        """Broadcast task completion via WebSocket and Telegram."""
        try:
            from core.llm_gateway import send_telegram_alert
            send_telegram_alert(
                f"✅ Task completed: {task['description'][:60]}\n\n{result[:300]}"
            )
        except Exception:
            pass

        try:
            if hasattr(self.kernel, '_webui_push') and self.kernel._webui_push:
                import json
                self.kernel._webui_push(json.dumps({
                    "type": "task_complete",
                    "task": task,
                    "result": result[:500],
                    "timestamp": datetime.now().isoformat()
                }))
        except Exception:
            pass

        try:
            if hasattr(self.kernel, 'memory'):
                self.kernel.memory.log_event(
                    "scheduled_task_complete",
                    f"Completed: {task['description'][:80]}",
                    result[:200],
                    importance=0.6
                )
        except Exception:
            pass

    def list_tasks(self) -> list:
        return self._tasks

    def remove_task(self, task_id: str) -> bool:
        before = len(self._tasks)
        self._tasks = [t for t in self._tasks if t["id"] != task_id]
        if len(self._tasks) < before:
            self._save()
            return True
        return False

    def register_as_tool(self, registry):
        scheduler = self

        def schedule_task(params: dict) -> dict:
            desc = params.get("task", "") or params.get("description", "")
            when = params.get("when", "") or params.get("schedule", "")
            if not desc or not when:
                return {"success": False, "error": "Provide 'task' and 'when' (e.g. 'every morning at 8am')"}
            task = scheduler.add_task(desc, natural=when)
            return {"success": True, "task": task, "message": f"Scheduled: '{desc}' {when} (cron: {task['cron']})"}

        def list_scheduled(params: dict) -> dict:
            tasks = scheduler.list_tasks()
            return {"success": True, "tasks": tasks, "count": len(tasks)}

        def remove_scheduled(params: dict) -> dict:
            task_id = params.get("task_id", "")
            ok = scheduler.remove_task(task_id)
            return {"success": ok}

        registry.register(
            "schedule_task",
            schedule_task,
            "Schedule a recurring task with natural language time: "
            "'every morning at 8am, summarize my emails'",
            {"task": {"type": "string", "required": True},
             "when": {"type": "string", "required": True}},
            "automation"
        )
        registry.register(
            "list_scheduled",
            list_scheduled,
            "List all scheduled recurring tasks",
            {},
            "automation"
        )
        registry.register(
            "remove_scheduled",
            remove_scheduled,
            "Remove a scheduled task by ID",
            {"task_id": {"type": "string", "required": True}},
            "automation"
        )

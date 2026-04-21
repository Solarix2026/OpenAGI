# Copyright (c) 2026 ApeironAILab
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/ApeironAILab/OpenAGI

"""
event_triggers.py — Event-driven task execution

Trigger types:
- file_created: watch a directory for new files
- file_modified: watch a file for changes
- system_metric: CPU/RAM threshold breach
- keyword: incoming Telegram message matching keyword
- http_webhook: POST to /webhook/{id} triggers task

All triggers stored in workspace/event_triggers.json
"""
import json
import threading
import time
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Callable

log = logging.getLogger("EventTriggers")
TRIGGERS_PATH = Path("./workspace/event_triggers.json")


class EventTriggerEngine:
    def __init__(self, kernel_ref):
        self.kernel = kernel_ref
        self._triggers = self._load()
        self._stop = threading.Event()
        self._file_states = {}  # path -> last_modified / hash
        self._thread = None

    def _load(self) -> list:
        try:
            return json.loads(TRIGGERS_PATH.read_text())
        except Exception:
            return []

    def _save(self):
        TRIGGERS_PATH.parent.mkdir(parents=True, exist_ok=True)
        TRIGGERS_PATH.write_text(json.dumps(self._triggers, indent=2))

    def add_trigger(self, trigger_type: str, config: dict, action: str) -> dict:
        """
        trigger_type: file_created | file_modified | keyword | system_metric | http_webhook
        config: {"path": "~/Downloads"} or {"keyword": "urgent"} etc.
        action: natural language task to run when triggered
        """
        trigger = {
            "id": f"trig_{int(time.time())}_{hashlib.md5(action.encode()).hexdigest()[:6]}",
            "type": trigger_type,
            "config": config,
            "action": action,
            "enabled": True,
            "fire_count": 0,
            "last_fired": None
        }
        self._triggers.append(trigger)
        self._save()
        log.info(f"[TRIGGER] Added {trigger_type}: {action[:50]}")
        return trigger

    def _check_file_triggers(self):
        import os

        for t in self._triggers:
            if not t.get("enabled"):
                continue

            if t["type"] == "file_created":
                watch_dir = Path(t["config"].get("path", ".")).expanduser()
                if not watch_dir.exists():
                    continue

                current_files = set(str(f) for f in watch_dir.iterdir() if f.is_file())
                known = set(self._file_states.get(str(watch_dir), []))
                new_files = current_files - known

                if new_files:
                    self._file_states[str(watch_dir)] = list(current_files)
                    for new_file in new_files:
                        self._fire(t, context=f"New file: {new_file}")

            elif t["type"] == "file_modified":
                watch_path = Path(t["config"].get("path", "")).expanduser()
                if not watch_path.exists():
                    continue

                mtime = watch_path.stat().st_mtime
                old_mtime = self._file_states.get(str(watch_path), 0)

                if mtime > old_mtime and old_mtime > 0:
                    self._file_states[str(watch_path)] = mtime
                    self._fire(t, context=f"File modified: {watch_path}")
                elif old_mtime == 0:
                    self._file_states[str(watch_path)] = mtime

    def _check_system_triggers(self):
        try:
            import psutil

            for t in self._triggers:
                if not t.get("enabled") or t["type"] != "system_metric":
                    continue

                metric = t["config"].get("metric", "cpu")
                threshold = float(t["config"].get("threshold", 90))

                if metric == "cpu":
                    value = psutil.cpu_percent(interval=0.1)
                elif metric == "ram":
                    value = psutil.virtual_memory().percent
                elif metric == "disk":
                    value = psutil.disk_usage('/').percent
                else:
                    continue

                # Cooldown: don't re-fire within 5 minutes
                last = t.get("last_fired", "")
                if last:
                    last_dt = datetime.fromisoformat(last)
                    if (datetime.now() - last_dt).seconds < 300:
                        continue

                if value > threshold:
                    self._fire(t, context=f"{metric.upper()} at {value:.1f}%")

        except ImportError:
            pass

    def _fire(self, trigger: dict, context: str = ""):
        log.info(f"[TRIGGER] Fired: {trigger['type']} — {trigger['action'][:50]}")
        trigger["fire_count"] = trigger.get("fire_count", 0) + 1
        trigger["last_fired"] = datetime.now().isoformat()
        self._save()

        task = f"{trigger['action']}. Context: {context}"
        try:
            result = self.kernel.process(task)

            # Notify via Telegram + WebUI
            try:
                from core.llm_gateway import send_telegram_alert
                send_telegram_alert(
                    f"⚡ Trigger fired [{trigger['type']}]:\n{result[:400]}"
                )
                if hasattr(self.kernel, '_webui_push') and self.kernel._webui_push:
                    self.kernel._webui_push(
                        f"⚡ Event: {context}\n{result[:300]}"
                    )
            except Exception as e:
                log.debug(f"Notification error: {e}")

        except Exception as e:
            log.error(f"[TRIGGER] Execution failed: {e}")

    def check_keyword(self, message: str):
        """Call this from run_telegram() for keyword triggers."""
        for t in self._triggers:
            if not t.get("enabled") or t["type"] != "keyword":
                continue
            keyword = t["config"].get("keyword", "").lower()
            if keyword and keyword in message.lower():
                self._fire(t, context=f"Keyword '{keyword}' in: {message[:80]}")

    def _run_loop(self):
        log.info("[TRIGGER] Engine started")
        while not self._stop.is_set():
            try:
                self._check_file_triggers()
                self._check_system_triggers()
            except Exception as e:
                log.debug(f"[TRIGGER] Cycle error: {e}")
            self._stop.wait(10)  # Check every 10 seconds

    def start(self):
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="EventTriggers"
        )
        self._thread.start()

    def stop(self):
        self._stop.set()

    def register_as_tool(self, registry):
        eng = self

        def add_trigger(params: dict) -> dict:
            ttype = params.get("type", "file_created")
            config = params.get("config", {})
            action = params.get("action", "")
            if not action:
                return {"success": False, "error": "Provide action to run when triggered"}
            t = eng.add_trigger(ttype, config, action)
            return {"success": True, "trigger": t}

        def list_triggers(params: dict) -> dict:
            return {"success": True, "triggers": eng._triggers}

        registry.register(
            "add_trigger",
            add_trigger,
            "Add an event trigger: run a task when file created/modified, "
            "keyword received, or system metric threshold exceeded",
            {"type": {"type": "string", "default": "file_created"},
             "config": {"type": "object"},
             "action": {"type": "string", "required": True}},
            "automation"
        )
        registry.register(
            "list_triggers",
            list_triggers,
            "List all active event triggers",
            {},
            "automation"
        )

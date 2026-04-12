"""
proactive_engine.py — Autonomous background intelligence

Loop runs every 5 minutes:
1. Fetch world events → BeepFilter → notify on relevant only
2. Check pending goals → attempt autonomous execution of low-risk ones
3. Run WillEngine cycle → add self-generated goals
4. HabitProfiler.predict_next_need → if confident, surface to user
5. Every hour: run CHRONOS check (not full cycle, just health)

Notification routing:
high relevance → immediate Telegram + voice
medium relevance → add to next morning briefing
low → discard silently
"""
import threading
import time
import logging
from datetime import datetime

log = logging.getLogger("Proactive")


class ProactiveEngine:
    def __init__(self, kernel_ref):
        self.k = kernel_ref
        self._thread = None
        self._stop = threading.Event()
        self._last_will_check = 0
        self._last_habit_check = 0
        self._briefing_buffer = []  # events to include in next briefing

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True, name="ProactiveEngine")
        self._thread.start()
        log.info("🔁 ProactiveEngine running")

    def _loop(self):
        time.sleep(30)  # Wait for kernel to fully initialize
        while not self._stop.is_set():
            try:
                self._run_cycle()
            except Exception as e:
                log.error(f"Proactive cycle error: {e}")
            self._stop.wait(300)  # 5 minute interval

    def _run_cycle(self):
        now = time.time()

        # ── World events → filter → notify ─────────────────────────
        if self.k.worldmonitor and self.k.beep:
            try:
                events = self.k.worldmonitor.get_events(limit=10)
                for event in events:
                    notify, mode = self.k.beep.should_notify(event)
                    if notify and mode == "immediate":
                        msg = f"📡 *{event.get('category', 'NEWS').upper()}*: {event.get('title', '')}"
                        if self.k.notify:
                            self.k.notify.send(msg, channels=["telegram"])
                        elif hasattr(self.k, '_notify_telegram'):
                            from llm_gateway import send_telegram_alert
                            send_telegram_alert(msg)
                    elif notify and mode == "briefing":
                        self._briefing_buffer.append(event)
            except Exception as e:
                log.debug(f"World event fetch error: {e}")

        # ── Will engine cycle (every 2h) ────────────────────────────
        if self.k.will and (now - self._last_will_check) > 7200:
            try:
                added = self.k.will.run_will_cycle()
                if added:
                    log.info(f"[WILL] Added {len(added)} autonomous goals")
                self._last_will_check = now
            except Exception as e:
                log.debug(f"Will cycle error: {e}")

        # ── Habit prediction (every 1h) ─────────────────────────────
        if self.k.habits and (now - self._last_habit_check) > 3600:
            try:
                prediction = self.k.habits.predict_next_need()
                if prediction:
                    log.info(f"[HABIT] Prediction: {prediction[:60]}")
                    # Only surface if not already in active conversation
                    recent = self.k.memory.get_recent_timeline(limit=1)
                    if recent:
                        from datetime import datetime as dt
                        last = dt.fromisoformat(recent[0]["ts"].replace("Z", ""))
                        idle_mins = (dt.now() - last).total_seconds() / 60
                        if idle_mins > 30:  # User idle >30min → surface prediction
                            from llm_gateway import send_telegram_alert
                            send_telegram_alert(f"💡 *Suggestion*: {prediction}")
                self._last_habit_check = now
            except Exception as e:
                log.debug(f"Habit prediction error: {e}")

        # ── Goal auto-execution (simple goals only) ─────────────────
        from goal_persistence import get_next_priority_goal, update_goal_status
        goal = get_next_priority_goal()
        if goal and goal.get("source") in ("conatus", "chronos"):
            # Only auto-execute system-generated low-risk goals
            if goal.get("type") in ("refresh", "research"):
                try:
                    log.info(f"[PROACTIVE] Auto-executing: {goal['description'][:60]}")
                    result = self.k.process(goal["description"])
                    update_goal_status(goal["id"], "completed", result[:200], memory=self.k.memory)
                except Exception as e:
                    log.debug(f"Auto-goal execution failed: {e}")

    def stop(self):
        self._stop.set()

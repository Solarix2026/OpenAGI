# Copyright (c) 2026 Solarix2026
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""
proactive_engine.py — Autonomous background intelligence (L4 Personalized)

Key improvements:
- Personalized nudges referencing user's actual context
- Idle detection before sending proactive messages
- Bilingual world event notifications
- Natural language (no "💡 Suggestion:" prefixes)
"""
import threading
import time
import logging
import os
from datetime import datetime

log = logging.getLogger("Proactive")


class ProactiveEngine:
    def __init__(self, kernel_ref):
        self.k = kernel_ref
        self._thread = None
        self._stop = threading.Event()
        self._last_will_check = 0
        self._last_habit_check = 0
        self._last_chronos_check = 0
        self._briefing_buffer = []
        self._seen_events = set()
        self._startup_time = time.time() # Grace period to avoid immediate nudges

        # Topic deduplication (24h cooldown)
        self._notified_topics = {}
        self._TOPIC_COOLDOWN = 86400

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True, name="ProactiveEngine")
        self._thread.start()
        log.info("🔁 ProactiveEngine running")

    def _loop(self):
        time.sleep(30)
        while not self._stop.is_set():
            try:
                self._run_cycle()
            except Exception as e:
                log.error(f"Proactive cycle error: {e}")
            self._stop.wait(300)

    def _get_idle_minutes(self) -> float:
        """Check how long user has been idle. Returns 0 if no history (not idle yet)."""
        # BUG-2 FIX: Startup gate - never report idle if kernel started less than 10 min ago
        startup_elapsed = time.time() - self._startup_time
        if startup_elapsed < 600: # 10 minute hard gate
            return 0.0
        recent = self.k.memory.get_recent_timeline(limit=1)
        if not recent:
            return 0.0 # No activity history = just started, not idle
        try:
            last = datetime.fromisoformat(recent[0]["ts"].replace("Z", ""))
            return (datetime.now() - last).total_seconds() / 60
        except:
            return 0.0

    def _detect_user_language(self) -> str:
        """Detect if user prefers Chinese or English."""
        recent = self.k.memory.search_events("", limit=20)
        user_msgs = [e["content"] for e in recent if e.get("event_type") == "user_message"]
        if not user_msgs:
            return "en"
        zh_count = sum(1 for m in user_msgs if any('\u4e00' <= c <= '\u9fff' for c in m))
        return "zh" if zh_count > len(user_msgs) * 0.4 else "en"

    def _get_recent_context(self) -> str:
        """Build context from recent user activity."""
        recent = self.k.memory.get_recent_timeline(limit=20)
        user_msgs = [e["content"] for e in recent if e.get("event_type") == "user_message"]
        projects = []
        for msg in user_msgs:
            if any(k in msg.lower() for k in ["project", "build", "create", "生成", "项目", "build", "app", "website"]):
                projects.append(msg[:50])
        return " | ".join(projects[-3:]) if projects else "general conversation"

    def _generate_personalized_nudge(self, prediction: str) -> str:
        """Generate a natural nudge referencing user's actual context."""
        from core.llm_gateway import call_nvidia

        recent_topics = self._get_recent_context()
        lang = "Chinese" if self._detect_user_language() == "zh" else "English"
        hour = datetime.now().hour
        time_note = "It's late night" if hour >= 22 or hour < 6 else ""

        prompt = f"""You are Jarvis. Generate a short, natural proactive message.

Context:
- User's recent activity: {recent_topics[:300]}
- Prediction/suggestion: {prediction}
- Language preference: {lang}
- Time note: {time_note if time_note else 'normal hours'}

Rules:
- Reference something SPECIFIC the user was working on (if relevant)
- Sound like you genuinely noticed something, not like an automated alert
- 1-2 sentences maximum
- Match the user's language ({lang})
- NEVER say "Suggestion:" or "💡 Suggestion" — just say it naturally

Example good:
"Hey, you were working on the video deck skill earlier — I noticed a new NVIDIA model dropped that might improve quality."

Example bad:
"💡 Suggestion: Consider updating your video deck skill."""

        return call_nvidia([{"role": "user", "content": prompt}], max_tokens=100, fast=True)

    def _format_event_notification(self, event: dict) -> str:
        """Format world event in user's language."""
        from core.llm_gateway import call_nvidia

        zh = self._detect_user_language() == "zh"
        lang = "Chinese (Simplified)" if zh else "English"

        prompt = f"""Summarize this news event in one sentence in {lang}:

Title: {event.get('title', '')}
Summary: {event.get('summary', '')[:200]}

Return one natural sentence. No emoji. No prefix. Just tell it."""

        return call_nvidia([{"role": "user", "content": prompt}], max_tokens=80, fast=True)

    def _run_cycle(self):
        """Main proactive cycle. Only nudge when user is idle."""
        # Only send Telegram if Telegram is configured
        telegram_enabled = bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))

        now = time.time()
        idle_mins = self._get_idle_minutes()

        # ── World events ──────────────────────────────────────────
        if self.k.worldmonitor and self.k.beep:
            try:
                events = self.k.worldmonitor.get_events(limit=8)
                immediate = []

                for event in events:
                    if event["url"] not in self._seen_events:
                        self._seen_events.add(event["url"])
                        notify, mode = self.k.beep.should_notify(event)
                        if notify and mode == "immediate" and idle_mins > 2:
                            immediate.append(event)
                        elif notify and mode == "briefing":
                            self._briefing_buffer.append(event)

                if immediate[:2]:
                    summaries = [self._format_event_notification(e) for e in immediate[:2]]
                    combined = " Meanwhile, ".join(summaries)
                    if self.k.notify and telegram_enabled:
                        self.k.notify.send(combined, channels=["telegram"])
                        # BUG-1 FIX: Also send to WebUI
                        if hasattr(self.k, '_webui_push') and self.k._webui_push:
                            self.k._webui_push(combined)
            except Exception as e:
                log.debug(f"World events error: {e}")

        # ── Will engine cycle (every 2h) ──────────────────────────
        if self.k.will and (now - self._last_will_check) > 7200:
            try:
                added = self.k.will.run_will_cycle()
                if added:
                    log.info(f"[WILL] {len(added)} autonomous goals added")
                self._last_will_check = now
            except Exception as e:
                log.debug(f"Will cycle error: {e}")

        # ── Habit nudge (only when idle > 45min, but not within 5min of startup) ─────────────────
        startup_grace = (time.time() - self._startup_time) > 300 # 5 minute grace period
        # BUG-2 FIX: Add startup_elapsed > 600 to prevent early nudges
        startup_elapsed = time.time() - self._startup_time
        if self.k.habits and idle_mins > 45 and (now - self._last_habit_check) > 3600 and startup_grace and startup_elapsed > 600:
            try:
                prediction = self.k.habits.predict_next_need()
                if prediction:
                    nudge = self._generate_personalized_nudge(prediction)
                    from core.llm_gateway import send_telegram_alert
                    send_telegram_alert(nudge)
                    # BUG-1 FIX: Also send to WebUI
                    if hasattr(self.k, '_webui_push') and self.k._webui_push:
                        self.k._webui_push(nudge)
                    log.info(f"[HABIT] Nudge sent (idle {idle_mins:.0f}min)")
                    self._last_habit_check = now
            except Exception as e:
                log.debug(f"Habit nudge error: {e}")

        # ── CHRONOS health check (every hour, not full cycle) ────
        if self.k.chronos and (now - self._last_chronos_check) > 3600:
            try:
                log.debug("[CHRONOS] Health check passed")
                self._last_chronos_check = now
            except Exception as e:
                log.debug(f"Chronos check error: {e}")

        # ── Auto-execute simple goals ─────────────────────────────
        from core.goal_persistence import get_next_priority_goal, update_goal_status
        goal = get_next_priority_goal()
        if goal and goal.get("source") in ("conatus", "chronos", "evolution"):
            if goal.get("type") in ("refresh", "research"):
                try:
                    log.info(f"[AUTO] Executing: {goal['description'][:60]}")
                    result = self.k.process(goal["description"])
                    update_goal_status(goal["id"], "completed", result[:200], memory=self.k.memory)
                except Exception as e:
                    log.debug(f"Auto-goal failed: {e}")

    def stop(self):
        self._stop.set()
        log.info("ProactiveEngine stopped")

    # Topic Deduplication
    def _topic_hash(self, text: str) -> str:
        import hashlib
        words = set(re.findall(r'\b\w{4,}\b', text.lower()))
        key = " ".join(sorted(list(words))[:5])
        return hashlib.md5(key.encode()).hexdigest()[:8]

    def _is_duplicate_topic(self, text: str) -> bool:
        h = self._topic_hash(text)
        if h in self._notified_topics:
            age = time.time() - self._notified_topics[h]
            if age < self._TOPIC_COOLDOWN:
                return True
        return False

    def _mark_notified(self, text: str):
        self._notified_topics[self._topic_hash(text)] = time.time()
        now = time.time()
        self._notified_topics = {k: v for k, v in self._notified_topics.items()
                                 if now - v < self._TOPIC_COOLDOWN * 2}

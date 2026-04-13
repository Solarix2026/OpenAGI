# Copyright (c) 2026 HackerTMJ
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""
jarvis_persona.py — Jarvis personality + morning briefings + greetings

Not hardcoded responses. NVIDIA generates everything based on context.
"""
import requests, logging
from datetime import datetime

log = logging.getLogger("Jarvis")


class JarvisPersona:
    def __init__(self, memory, google=None, voice=None, worldmonitor=None):
        self.memory = memory
        self.google = google
        self.voice = voice
        self.worldmonitor = worldmonitor

    def morning_briefing(self, city: str = None) -> str:
        from core.llm_gateway import call_nvidia
        from core.user_context import UserContextProvider
        from core.goal_persistence import load_goal_queue, get_pending_count

        ctx_provider = UserContextProvider()
        loc = ctx_provider.get_location()
        city = city or loc.get("city", "Kuala Lumpur")
        weather = ctx_provider.get_weather(city)
        time_ctx = ctx_provider.get_time_context()

        # Gather components
        components = {
            "weather": weather.get("summary", "weather unavailable"),
            "time": time_ctx["greeting"],
            "pending_goals": get_pending_count(),
        }

        if self.google:
            try:
                emails = self.google.get_unread_emails(max_results=1)
                components["unread_emails"] = len(emails)
                events = self.google.get_today_events()
                components["today_events"] = len(events)
            except Exception:
                pass

        if self.worldmonitor:
            try:
                components["top_headline"] = self.worldmonitor.get_top_headline()
            except Exception:
                pass

        # L4: Give NVIDIA the FACTS. Let it decide structure.
        prompt = f"""You are Jarvis. Generate a morning briefing for your boss.

Context:
- Time: {time_ctx['period']} ({time_ctx['time_str']})
{"Note: It's very late — adapt tone accordingly." if time_ctx.get('is_late_night') else ""}
- Location: {city}
- Weather: {components['weather']}
- Pending goals: {components['pending_goals']}
{f"- Unread emails: {components['unread_emails']}" if 'unread_emails' in components else ""}
{f"- Today's calendar: {components.get('today_events', 0)} events" if 'today_events' in components else ""}
{f"- Top news: {components.get('top_headline','')}" if 'top_headline' in components else ""}

Deliver this briefing in your natural Jarvis style. Adapt length and tone to the time of day and what's actually worth saying. Don't force structure if there's nothing to report on a dimension.

User's preferred language: {"Chinese" if self._detect_user_language() == "zh" else "English"}
"""
        briefing = call_nvidia(
            [{"role": "user", "content": prompt}],
            max_tokens=200,
            fast=True
        )

        self.memory.log_event("morning_briefing", briefing, importance=0.6)

        if self.voice:
            try:
                self.voice.speak(briefing)
            except Exception:
                pass

        return briefing

    def generate_greeting(self, last_topic: str = "") -> str:
        from core.llm_gateway import call_nvidia
        from core.user_context import UserContextProvider

        ctx = UserContextProvider()
        t = ctx.get_time_context()
        w = ctx.get_weather()

        prompt = f"""Generate a 1-sentence Jarvis greeting.

Time: {t['greeting']} ({t['time_str']})
Weather: {w.get('summary', 'unknown')}
Last known topic: {last_topic or 'none'}

Sound natural, not robotic. Vary the greeting each time."""

        return call_nvidia(
            [{"role": "user", "content": prompt}],
            max_tokens=80,
            fast=True
        )

    def _detect_user_language(self) -> str:
        """Check recent messages to detect language preference."""
        recent = self.memory.search_events("", limit=10)
        user_msgs = [e["content"] for e in recent if e.get("event_type") == "user_message"]
        zh_count = sum(1 for m in user_msgs if any('\u4e00' <= c <= '\u9fff' for c in m))
        return "zh" if zh_count > len(user_msgs) * 0.4 else "en"

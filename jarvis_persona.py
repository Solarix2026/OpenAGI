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
        from llm_gateway import call_nvidia
        from user_context import UserContextProvider
        from goal_persistence import load_goal_queue, get_pending_count

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

        prompt = f"""Generate a Jarvis morning briefing based on:
{components}

Requirements:
- Start with time greeting: "{time_ctx['greeting']} sir."
- Mention weather in {city}
- If emails: mention unread count
- If goals: mention pending count
- If headline: mention top world story in 1 sentence
- End with a brief "what do you need today?"
- Max 4 sentences total. Warm, precise, Jarvis-style.
- Language: English (unless user is Chinese-speaking based on memory)
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
        from llm_gateway import call_nvidia
        from user_context import UserContextProvider

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

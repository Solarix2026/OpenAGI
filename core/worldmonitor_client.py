# Copyright (c) 2026 ApeironAILab
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/ApeironAILab/OpenAGI

"""
worldmonitor_client.py — Real-time global event stream

Fetches from RSS feeds. Summarizes via NVIDIA into Jarvis-style briefings.
Opens WorldMonitor dashboard in browser for visual exploration.

Demo behavior (from reference video):
  User: "tell me what's happening in the world"
  Jarvis: [fetches headlines] → natural 3-sentence summary → opens dashboard
"""
import feedparser, re, logging, webbrowser, os
from datetime import datetime
from threading import Thread, Event

log = logging.getLogger("WorldMonitor")

RSS_FEEDS = {
    "world": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "technology": "https://feeds.feedburner.com/TechCrunch",
    "ai": "https://www.artificialintelligence-news.com/feed/",
    "markets": "https://feeds.reuters.com/reuters/businessNews",
    "geopolitics": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "science": "https://www.sciencedaily.com/rss/all.xml",
}

DASHBOARD_URL = os.getenv("WORLDMONITOR_URL", "https://worldmonitor.app")


class WorldMonitorClient:
    def __init__(self):
        self._seen_urls: set = set()
        self._stop = Event()

    def get_events(self, categories=None, limit=20) -> list:
        cats = categories or ["world", "technology", "ai", "geopolitics"]
        all_events, seen_urls = [], set()

        for cat in cats:
            url = RSS_FEEDS.get(cat)
            if not url:
                continue
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:limit]:
                    u = entry.get("link", "")
                    if u in seen_urls:
                        continue
                    seen_urls.add(u)
                    all_events.append({
                        "title": entry.get("title", ""),
                        "summary": re.sub(
                            r"<[^>]+>", "",
                            entry.get("summary", entry.get("description", ""))
                        )[:300],
                        "url": u,
                        "source": feed.feed.get("title", cat),
                        "category": cat,
                        "published": entry.get("published", datetime.now().isoformat()),
                    })
            except Exception as e:
                log.debug(f"RSS fetch failed [{cat}]: {e}")

        return all_events[:limit]

    def summarize_for_briefing(self, events: list, user_ctx: str = "") -> str:
        """
        NVIDIA generates a natural Jarvis-style world briefing.
        Mirrors demo: concise, conversational, mentions 2-3 key stories.
        """
        from core.llm_gateway import call_nvidia

        headlines = "\n".join(
            f"- [{e['category'].upper()}] {e['title']}: {e['summary'][:120]}"
            for e in events[:8]
        )

        prompt = f"""You are Jarvis, briefing your boss on world events.

{user_ctx}

Current headlines:
{headlines}

Deliver a natural 3-4 sentence briefing:
- Lead with the most significant geopolitical or high-impact story
- Group related events naturally ("tensions in X are escalating following...")
- Mention 2-3 stories total, not more
- End with: "Let me pull up the WorldMonitor so you can see the full picture."
- Sound like Iron Man's Jarvis, not a news anchor
- Match user's language from context (English or Chinese)
"""
        msgs = [{"role": "user", "content": prompt}]
        return call_nvidia(msgs, max_tokens=300, fast=True)

    def open_dashboard(self) -> str:
        webbrowser.open(DASHBOARD_URL)
        log.info(f"[WorldMonitor] Dashboard opened: {DASHBOARD_URL}")
        return DASHBOARD_URL

    def get_top_headline(self) -> str:
        events = self.get_events(categories=["world"], limit=3)
        return events[0]["title"] if events else "No headlines available"

    def get_relevant_events(self, context: str, limit=5) -> list:
        ctx_words = set(re.findall(r"\w+", context.lower()))
        all_events = self.get_events()
        scored = []
        for e in all_events:
            words = set(re.findall(r"\w+", (e["title"] + " " + e["summary"]).lower()))
            score = len(ctx_words & words) / max(len(ctx_words), 1)
            if score > 0.15:
                scored.append((score, e))
        scored.sort(reverse=True)
        return [e for _, e in scored[:limit]]

    def start_monitoring(self, callback, interval=300):
        def _loop():
            while not self._stop.is_set():
                for e in self.get_events():
                    if e["url"] not in self._seen_urls:
                        self._seen_urls.add(e["url"])
                        try:
                            callback(e)
                        except Exception:
                            pass
                self._stop.wait(interval)
        Thread(target=_loop, daemon=True, name="WorldMonitor").start()

# Copyright (c) 2026 HackerTMJ
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/HackerTMJ/OpenAGI

"""
beep_filter.py — Noise filter for all proactive events before they reach the user.

Prevents notification spam. Surfaces only what's genuinely relevant.
"""
import time
import logging
import re
from collections import Counter
from typing import Tuple

log = logging.getLogger("BeepFilter")


class BeepFilter:
    def __init__(self, memory):
        self.memory = memory
        self._profile_cache: dict = {}
        self._profile_age: float = 0

    def _get_interest_profile(self) -> dict:
        """Build interest profile from recent user messages (cached 30min)."""
        if time.time() - self._profile_age < 1800 and self._profile_cache:
            return self._profile_cache

        try:
            events = self.memory.search_events("", limit=100)
            user_msgs = [e["content"] for e in events if e.get("event_type") == "user_message"]

            words = re.findall(r'\b\w{4,}\b', " ".join(user_msgs).lower())

            # Filter stopwords
            stops = {"that", "this", "with", "have", "from", "they", "what", "your", "will", "been",
                     "than", "only", "other", "some", "time", "very", "when", "come", "here",
                     "just", "like", "over", "also", "back", "after", "use", "two", "how",
                     "its", "our", "work", "first", "well", "way", "even", "new", "want"}

            profile = {w: c for w, c in Counter(words).most_common(30) if w not in stops}
            self._profile_cache = profile
            self._profile_age = time.time()
            return profile
        except Exception as e:
            log.debug(f"Profile build failed: {e}")
            return {}

    def relevance_score(self, event: dict) -> float:
        """Fast TF-IDF keyword overlap score. No LLM call for speed."""
        profile = self._get_interest_profile()
        if not profile:
            return 0.3

        event_text = str(event.get("title", "")) + " " + str(event.get("summary", "")) + " " + str(event.get("content", ""))
        event_words = set(re.findall(r'\b\w{4,}\b', event_text.lower()))
        profile_words = set(profile.keys())

        if not profile_words:
            return 0.3

        overlap = len(profile_words & event_words)
        return min(1.0, overlap / max(len(profile_words) * 0.3, 1))

    def should_notify(self, event: dict) -> Tuple[bool, str]:
        """Returns (notify, mode). mode: 'immediate' | 'briefing' | 'discard'"""
        score = self.relevance_score(event)

        if score > 0.6:
            return True, "immediate"
        if score > 0.35:
            return True, "briefing"

        return False, "discard"

    def filter_events(self, events: list, threshold: float = 0.35) -> list:
        """Filter events below relevance threshold."""
        return [e for e in events if self.relevance_score(e) >= threshold]

    def should_interrupt(self, user_input: str) -> bool:
        """Check if current message indicates user is busy/do-not-disturb."""
        busy_signals = ["don't interrupt", "busy", "focus", "concentrating", "meeting",
                      "别打扰", "忙", "会议中", "专注"]
        return any(s in user_input.lower() for s in busy_signals)

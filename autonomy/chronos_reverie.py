# Copyright (c) 2026 Solarix2026
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""
chronos_reverie.py — Nightly autonomous review cycle

Runs automatically at 3:00 AM.
Sequence:
1. Dialectic self-critique (WillEngine.dialectic_review) on top 3 failure categories
2. Knowledge consolidation (compress episodic → semantic patterns)
3. Skill gap repair (EvolutionEngine.run_gap_detection)
4. Tool health check (invent replacements for failing tools)
5. Goal queue cleanup (archive stale, reprioritize active)
6. Generate morning briefing draft (saved to memory)
7. Send Telegram summary of what was done
"""

import threading
import time
import logging
from datetime import datetime
from pathlib import Path

log = logging.getLogger("CHRONOS")


class ChronosReverie:
    def __init__(self, kernel_ref):
        self.kernel = kernel_ref
        self._thread = None
        self._running = False
        self._interval = int(Path("./workspace/chronos_interval.txt") if Path("./workspace/chronos_interval.txt").exists() else "300")

    def start(self):
        """Start background thread that wakes at 3am."""
        self._running = True
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True, name="CHRONOS_REVERIE")
        self._thread.start()
        log.info("⏰ CHRONOS_REVERIE scheduled (runs at 03:00)")

    def _scheduler_loop(self):
        while self._running:
            now = datetime.now()
            # Run between 03:00 and 03:15
            if now.hour == 3 and now.minute < 15:
                last_run = self.kernel.memory.get_meta_knowledge("chronos_last_run")
                last_date = last_run.get("content", "") if last_run else ""
                today = now.strftime("%Y-%m-%d")
                if last_date != today:
                    log.info("🌙 CHRONOS_REVERIE starting nightly cycle")
                    self.kernel.memory.update_meta_knowledge("chronos_last_run", today)
                    self.run_cycle()
            time.sleep(300)  # Check every 5 minutes

    def run_cycle(self) -> dict:
        """Full nightly review cycle. Returns summary dict."""
        from core.llm_gateway import send_telegram_alert
        results = {}
        # Disabled status update - too noisy. Summary will be sent at end instead.
        # send_telegram_alert("🌙 *CHRONOS_REVERIE starting...*")

        # Step 1: Dialectic review on recent failures
        if self.kernel.will:
            for topic in ["tool failures this week", "clarification requests that were excessive", "goals that went unresolved"]:
                result = self.kernel.will.dialectic_review(topic)
                if result.get("action_item"):
                    from core.goal_persistence import add_to_goal_queue
                    add_to_goal_queue(
                        f"[REVERIE] {result['action_item']}",
                        priority=0.7,
                        source="chronos",
                        memory=self.kernel.memory
                    )
            results["dialectic"] = "✅ complete"

        # Step 2: Knowledge consolidation
        timeline = self.kernel.memory.get_recent_timeline(limit=50)
        events_text = "\n".join(f"[{e['event_type']}] {e['content'][:80]}" for e in timeline)
        consolidation_prompt = f"""Analyze these recent AI agent events and extract:
1. Recurring patterns (what does the user frequently need?)
2. Capability gaps (what failed repeatedly?)
3. Knowledge that should be retained long-term

Events: {events_text}

Return JSON: {{"patterns": [...], "gaps": [...], "retain": [...]}}"""
        from core.llm_gateway import call_nvidia
        import json
        import re
        raw = call_nvidia([{"role": "user", "content": consolidation_prompt}], max_tokens=600)
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            consolidated = json.loads(m.group(0))
            self.kernel.memory.update_meta_knowledge("knowledge_consolidation", consolidated)
            results["consolidation"] = consolidated

        # Step 3: Evolution cycle
        if self.kernel.evolution:
            gaps = self.kernel.evolution.run_gap_detection()
            results["gaps_detected"] = len(gaps)

        # Step 4: Tool health repair
        if self.kernel.will:
            will_goals = self.kernel.will.run_will_cycle()
            results["will_goals_added"] = len(will_goals)

        # Step 5: Habit profile refresh
        if self.kernel.habits:
            self.kernel.habits.build_profile()
            results["habit_profile"] = "✅ refreshed"

        # Step 6: Generate morning briefing draft
        if self.kernel.jarvis:
            try:
                draft = self.kernel.jarvis.morning_briefing()
                self.kernel.memory.update_meta_knowledge("morning_briefing_draft", draft)
                results["briefing"] = "✅ ready"
            except Exception:
                pass

        # Step 7: Report
        summary = f"""🌙 *CHRONOS_REVERIE Complete*
Dialectic: {results.get('dialectic', 'skip')}
Gaps found: {results.get('gaps_detected', 0)}
Will goals: {results.get('will_goals_added', 0)}
Habits: {results.get('habit_profile', 'skip')}
Briefing: {results.get('briefing', 'skip')}"""
        send_telegram_alert(summary)
        log.info(f"CHRONOS_REVERIE complete: {results}")
        return results

    def stop(self):
        self._running = False

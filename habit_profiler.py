"""
habit_profiler.py — Learn user's behavioral patterns. Predict needs. Proactively suggest.

Not just "you often ask about X" — model the USER'S daily rhythm.
"""
import json
import re
import logging
from datetime import datetime
from collections import Counter, defaultdict

log = logging.getLogger("HabitProfiler")


class HabitProfiler:
    def __init__(self, memory):
        self.memory = memory

    def build_profile(self) -> dict:
        """
        Analyze episodic memory to extract:
        - Active hours (what times does user interact?)
        - Topic distribution (what domains, what languages?)
        - Request patterns (what types of tasks?)
        - Emotional indicators (frustrated queries, praise, etc.)

        Returns profile dict stored in meta_knowledge["habit_profile"].
        """
        try:
            events = self.memory.search_events("", limit=200)
            user_events = [e for e in events if e.get("event_type") == "user_message"]

            hours = Counter()
            topics = Counter()
            lang_cn = 0
            task_types = Counter()

            for e in user_events:
                ts = e.get("ts", "")
                if ts:
                    try:
                        h = datetime.fromisoformat(ts.replace("Z", "")).hour
                        hours[h] += 1
                    except Exception:
                        pass

                content = e.get("content", "")
                words = re.findall(r'\b\w{4,}\b', content.lower())

                # Extract topics (nouns, verbs)
                topics.update([w for w in words if w not in {
                    "that", "this", "with", "have", "from", "they", "what", "your",
                    "will", "been", "than", "only", "other", "some", "time"
                }])

                # Detect language
                if any('\u4e00' <= c <= '\u9fff' for c in content):
                    lang_cn += 1

                # Detect task type
                content_lower = content.lower()
                if any(w in content_lower for w in ["open", "打开", "start", "launch"]):
                    task_types["app_launch"] += 1
                if any(w in content_lower for w in ["search", "搜索", "find", "look for"]):
                    task_types["search"] += 1
                if any(w in content_lower for w in ["write", "create", "build", "make", "写", "创建"]):
                    task_types["creation"] += 1
                if any(w in content_lower for w in ["check", "status", "what's", "how is", "状态"]):
                    task_types["status_check"] += 1

            profile = {
                "peak_hours": [h for h, _ in hours.most_common(3)],
                "top_topics": [w for w, _ in topics.most_common(15)],
                "preferred_language": "zh" if lang_cn > len(user_events) * 0.4 else "en",
                "total_interactions": len(user_events),
                "task_patterns": dict(task_types.most_common(5)),
                "last_updated": datetime.now().isoformat()
            }

            self.memory.update_meta_knowledge("habit_profile", profile)
            log.info(f"[HABIT] Profile built: {len(user_events)} interactions")
            return profile

        except Exception as e:
            log.error(f"Build profile failed: {e}")
            return {}

    def get_profile(self) -> dict:
        """Get cached profile or build new one."""
        try:
            cached = self.memory.get_meta_knowledge("habit_profile")
            if cached and cached.get("content"):
                return cached["content"]
        except Exception:
            pass
        return self.build_profile()

    def predict_next_need(self) -> str | None:
        """
        Based on: current time, habit profile, recent goals, recent events.
        Ask NVIDIA: what does this user likely need right now?
        Returns suggestion string or None if no confident prediction.
        """
        try:
            from llm_gateway import call_nvidia

            profile_data = self.get_profile()
            hour = datetime.now().hour
            recent_goals = []
            try:
                from goal_persistence import load_goal_queue
                recent_goals = [g.get("description", "") for g in load_goal_queue()[:5]]
            except Exception:
                pass

            prompt = f"""User habit profile: {json.dumps(profile_data, ensure_ascii=False)}
Current hour: {hour}
Pending goals: {recent_goals}

What does this user MOST LIKELY need right now, based on their patterns? Be specific. If no confident prediction, say null.

Return JSON: {{"prediction": "specific suggestion or null", "confidence": 0.0-1.0}}"""

            raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=120, fast=True)
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                d = json.loads(m.group(0))
                if d.get("confidence", 0) > 0.65:
                    return d.get("prediction")

        except Exception as e:
            log.debug(f"Prediction failed: {e}")

        return None

    def should_proactive_suggest(self) -> bool:
        """Check if user is likely receptive to proactive suggestions now."""
        try:
            profile = self.get_profile()
            current_hour = datetime.now().hour
            peak_hours = profile.get("peak_hours", [])

            # Only suggest during typical active hours
            if peak_hours and current_hour not in peak_hours:
                return False

            # Check last interaction time
            recent = self.memory.get_recent_timeline(limit=1)
            if recent:
                last_ts = recent[0].get("ts", "")
                if last_ts:
                    mins_since = (datetime.now() - datetime.fromisoformat(last_ts.replace("Z", ""))).total_seconds() / 60
                    # Only suggest if user has been idle 30+ minutes
                    return mins_since > 30

        except Exception:
            pass

        return False

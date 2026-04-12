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

    def _get_recent_activity_summary(self) -> str:
        """Get summary of recent user activity from memory."""
        try:
            recent = self.memory.get_recent_timeline(limit=20)
            activities = []
            for e in recent:
                if e.get("event_type") == "user_message":
                    activities.append(e.get("content", "")[:80])
                elif e.get("event_type") == "tool_execution":
                    activities.append(f"[Tool: {e.get('content', '')}]")
            return " | ".join(activities[:5]) if activities else "no recent activity"
        except:
            return "unknown"

    def _get_current_context(self) -> dict:
        """Gather real-time context for prediction."""
        ctx = {
            "hour": datetime.now().hour,
            "weekday": datetime.now().strftime("%A"),
            "is_weekend": datetime.now().weekday() >= 5,
        }

        # Try to get weather
        try:
            from core.user_context import UserContextProvider
            uc = UserContextProvider()
            weather = uc.get_weather()
            ctx["weather"] = weather.get("summary", "unknown")
            ctx["location"] = uc.get_location().get("city", "unknown")
        except:
            ctx["weather"] = "unknown"
            ctx["location"] = "unknown"

        return ctx

    def predict_next_need(self) -> str | None:
        """
        L4: Predict user's next need based on comprehensive context.
        Combines: habit profile + real-time context + recent activity + world events.
        """
        try:
            from core.llm_gateway import call_nvidia

            # Gather all context
            profile_data = self.get_profile()
            context = self._get_current_context()
            recent_activity = self._get_recent_activity_summary()
            hour = datetime.now().hour

            # Get recent goals
            recent_goals = []
            try:
                from core.goal_persistence import load_goal_queue
                goals = load_goal_queue()
                recent_goals = [g.get("description", "") for g in goals[:3] if g.get("status") == "pending"]
            except:
                pass

            # Detect language preference
            lang = "zh" if profile_data.get("preferred_language") == "zh" else "en"

            # Get one relevant world event hint if possible
            world_hint = ""
            try:
                from core.worldmonitor_client import WorldMonitorClient
                wm = WorldMonitorClient()
                events = wm.get_events(limit=3)
                if events:
                    # Check if any event relates to user's top topics
                    top_topics = set(profile_data.get("top_topics", []))
                    for e in events:
                        if any(t in e.get("title", "").lower() or t in e.get("category", "").lower() for t in top_topics):
                            world_hint = f"Relevant world event: {e.get('title', '')}"
                            break
            except:
                pass

            # Time-of-day contextual notes
            time_note = ""
            if 6 <= hour < 9:
                time_note = "Early morning - user likely starting day"
            elif 9 <= hour < 12:
                time_note = "Morning work hours - productive time"
            elif 12 <= hour < 14:
                time_note = "Lunch/midday - possible break time"
            elif 14 <= hour < 18:
                time_note = "Afternoon - continued work"
            elif 18 <= hour < 22:
                time_note = "Evening - winding down or personal projects"
            else:
                time_note = "Late night - user might need summaries or async tasks"

            prompt = f"""You are Jarvis, an intelligent assistant. Predict what the user needs RIGHT NOW.

## User Context
- Active hours: {profile_data.get("peak_hours", ["unknown"])}
- Common topics: {profile_data.get("top_topics", ["unknown"])[:5]}
- Language: {lang}
- Recent activity: {recent_activity[:200]}

## Real-time Context
- Time: {hour}:00 ({time_note})
- Location: {context.get("location", "unknown")}
- Weather: {context.get("weather", "unknown")}
- Day: {context.get("weekday")} ({"weekend" if context.get("is_weekend") else "weekday"})

## Current State
- Pending goals: {recent_goals if recent_goals else "none"}
- {world_hint if world_hint else "No urgent world events"}

## Task
Based on ALL the above, what would be the MOST HELFUL prediction of their next need?

Rules:
1. Be SPECIFIC - "check email" is generic; "summarize the morning briefing" is specific
2. Reference actual context - mention the weather, time of day, or recent activity if relevant
3. Consider the user's patterns - if they code at night, suggest code-related tasks
4. Language: Respond in {lang.upper()} to match user preference
5. Confidence: Only predict if you're genuinely confident (>=0.7)

Return JSON: {{"prediction": "specific suggestion or null", "confidence": 0.0-1.0, "reasoning": "why this prediction"}}"""

            raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=200, fast=True)
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                d = json.loads(m.group(0))
                pred = d.get("prediction")
                conf = d.get("confidence", 0)
                if pred and pred.lower() != "null" and conf >= 0.7:
                    log.info(f"[HABIT] Predicted (conf={conf:.2f}): {pred[:60]}")
                    return pred

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

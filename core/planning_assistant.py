# core/planning_assistant.py
"""
AI-powered planning assistant. Converts natural language goals into structured task breakdown + scheduling.
"""  # noqa: E501
import json
import re
import logging
from datetime import datetime
from core.llm_gateway import call_nvidia

log = logging.getLogger("PlanningAssistant")


class PlanningAssistant:
    def __init__(self, memory, cron_scheduler=None, goal_queue_add_fn=None):
        self.memory = memory
        self.cron = cron_scheduler
        self.add_goal = goal_queue_add_fn

    def create_plan(self, objective: str, timeframe: str = "1 week") -> dict:
        """Break down a high-level objective into scheduled tasks."""
        today = datetime.now().strftime("%Y-%m-%d (%A)")
        prompt = f"""Create a detailed action plan for: "{objective}"
Timeframe: {timeframe}
Today: {today}

Break it down into concrete, actionable tasks with specific schedules.
Return JSON:
{{
    "objective": "main goal",
    "phases": [
        {{
            "name": "Phase 1: Research",
            "duration": "2 days",
            "tasks": [
                {{
                    "task": "specific action to take",
                    "schedule": "natural language: tomorrow at 9am",
                    "estimated_duration": "30 minutes",
                    "deliverable": "what this produces",
                    "requires_human": true,
                    "requires_ai_only": true
                }}
            ]
        }}
    ],
    "success_metrics": ["how to measure completion"],
    "risks": ["potential blockers"],
    "first_action": "do this TODAY"
}}"""
        raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=1500)
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if not m:
            return {"success": False, "error": "Planning failed"}
        try:
            plan = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid plan JSON"}

        # Auto-schedule AI-only tasks
        scheduled = []
        if self.cron:
            for phase in plan.get("phases", []):
                for task in phase.get("tasks", []):
                    if task.get("requires_ai_only") and not task.get("requires_human"):
                        cron_task = self.cron.add_task(
                            task["task"],
                            natural=task.get("schedule", "tomorrow at 9am")
                        )
                        scheduled.append(cron_task["id"])

        # Add main objective to goal queue
        if self.add_goal:
            self.add_goal(
                f"[PLAN] {plan.get('objective', objective)}",
                priority=0.9,
                source="planning_assistant"
            )

        # Store plan in memory
        self.memory.update_meta_knowledge(
            f"plan_{re.sub(r'[^a-z0-9]', '_', objective.lower()[:20])}",
            plan
        )

        return {
            "success": True,
            "plan": plan,
            "tasks_scheduled": len(scheduled),
            "first_action": plan.get("first_action", "See plan above"),
            "objective": objective
        }

    def suggest_next_action(self, context: str = "") -> str:
        """Based on current goals and habits, suggest what to do next."""
        from core.goal_persistence import load_goal_queue
        goals = load_goal_queue()
        pending = [g for g in goals if g.get("status") == "pending"][:3]
        recent = self.memory.get_recent_timeline(limit=10)
        recent_str = "; ".join(e.get("content", "")[:50] for e in recent[:5])

        prompt = f"""You are a productivity coach. Suggest the single best next action.
Pending goals: {[g.get('description','')[:60] for g in pending]}
Recent activity: {recent_str}
User context: {context or 'none'}
Time: {datetime.now().strftime('%H:%M on %A')}

Return ONE specific actionable suggestion in 1-2 sentences. Be concrete."""
        return call_nvidia([{"role": "user", "content": prompt}], max_tokens=100, fast=True)


def register_planning_tools(registry, planning_assistant):
    pa = planning_assistant

    def create_plan(params: dict) -> dict:
        obj = params.get("objective", "") or params.get("goal", "")
        timeframe = params.get("timeframe", params.get("duration", "1 week"))
        if not obj:
            return {"success": False, "error": "Provide objective"}
        return pa.create_plan(obj, timeframe)

    def suggest_next(params: dict) -> dict:
        ctx = params.get("context", "")
        suggestion = pa.suggest_next_action(ctx)
        return {"success": True, "suggestion": suggestion}

    registry.register(
        "create_plan",
        create_plan,
        "Create a detailed action plan with scheduled tasks for any goal or project. Auto-schedules AI-executable tasks.",
        {
            "objective": {"type": "string", "required": True},
            "timeframe": {"type": "string", "default": "1 week"}
        },
        "planning"
    )
    registry.register(
        "suggest_next_action",
        suggest_next,
        "Get AI suggestion for the best next action based on current goals and recent activity",
        {"context": {"type": "string", "optional": True}},
        "planning"
    )

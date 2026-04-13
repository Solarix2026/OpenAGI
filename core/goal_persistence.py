# Copyright (c) 2026 HackerTMJ (门牌号3号)
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/HackerTMJ/OpenAGI

"""
goal_persistence.py — Cross-session goal queue

Goals survive restarts. Priority queue sorted by urgency × importance.
"""
import json, logging
from pathlib import Path
from datetime import datetime
from typing import Optional

log = logging.getLogger("Goals")
GOALS_PATH = Path("./workspace/goal_queue.json")


def _load() -> list:
    try:
        return json.loads(GOALS_PATH.read_text())
    except Exception:
        return []


def _save(goals: list):
    GOALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOALS_PATH.write_text(json.dumps(goals, indent=2, ensure_ascii=False))


def load_goal_queue(memory=None) -> list:
    return _load()


def add_to_goal_queue(description: str, priority: float = 0.5, source: str = "user", memory=None) -> dict:
    goals = _load()
    goal = {
        "id": f"g_{int(datetime.now().timestamp())}",
        "description": description,
        "priority": priority,
        "status": "pending",
        "source": source,
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
    }
    goals.append(goal)
    goals.sort(key=lambda g: g.get("priority", 0.5), reverse=True)
    _save(goals)

    if memory:
        memory.log_event("goal_added", description, {"id": goal["id"]}, importance=0.7)

    return goal


def update_goal_status(goal_id: str, status: str, result: str = "", memory=None):
    goals = _load()
    for g in goals:
        if g["id"] == goal_id:
            g["status"] = status
            g["result"] = result
            g["updated"] = datetime.now().isoformat()
            break
    _save(goals)


def get_next_priority_goal() -> Optional[dict]:
    goals = _load()
    for g in goals:
        if g.get("status") == "pending":
            return g
    return None


def get_pending_count() -> int:
    return sum(1 for g in _load() if g.get("status") == "pending")

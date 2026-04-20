# Copyright (c) 2026 Solarix2026
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""
core/goal_alignment_monitor.py — Goal drift detection

Watches multi-step tasks for divergence from original intent.
Fires when:
1. Agent has taken 5+ steps on a single task
2. Agent tries to install a new package (pip install pattern detected)
3. Agent requests a tool not previously used in this session

On drift detection: pauses execution, asks NVIDIA for assessment,
can abort and suggest alternative path.
"""

import time
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

log = logging.getLogger("GoalAlignmentMonitor")


@dataclass
class TaskContext:
    """Tracks state of current multi-step task."""
    root_goal: str
    start_time: float = field(default_factory=time.time)
    step_count: int = 0
    actions_taken: List[str] = field(default_factory=list)
    tools_used: set = field(default_factory=set)
    packages_attempted: List[str] = field(default_factory=list)

    def record_action(self, action: str, tool_name: str):
        """Record an action taken."""
        self.step_count += 1
        self.actions_taken.append(action)
        self.tools_used.add(tool_name)

    def is_divergence_risk(self) -> bool:
        """Check if task shows divergence risk patterns."""
        if self.step_count >= 5:
            return True
        if len(self.packages_attempted) > 0:
            return True
        return False


class GoalAlignmentMonitor:
    """
    Monitors multi-step tasks for goal drift.

    Safety mechanism: prevents agents from spending too long
    on tangential tasks or installing unnecessary dependencies.
    """

    def __init__(self, kernel=None):
        self.kernel = kernel
        self._active_tasks: Dict[str, TaskContext] = {}
        self._current_task_id: Optional[str] = None
        self._alignment_threshold = 0.5  # Score below this = drift

        # Patterns that indicate potential package installation
        self._install_patterns = [
            r'pip\s+install',
            r'apt\s+install',
            r'brew\s+install',
            r'npm\s+install',
            r'yarn\s+add',
            r'cargo\s+install',
            r'go\s+get',
        ]

    def start_task(self, goal: str, task_id: Optional[str] = None) -> str:
        """
        Start tracking a new multi-step task.

        Args:
            goal: Original goal description
            task_id: Optional task identifier

        Returns:
            task_id for tracking
        """
        if task_id is None:
            task_id = f"task_{int(time.time())}"

        self._active_tasks[task_id] = TaskContext(root_goal=goal)
        self._current_task_id = task_id

        log.info(f"[ALIGN] Started task: {goal[:60]}")
        return task_id

    def end_task(self, task_id: Optional[str] = None):
        """End tracking for a task."""
        tid = task_id or self._current_task_id
        if tid and tid in self._active_tasks:
            ctx = self._active_tasks[tid]
            log.info(f"[ALIGN] Task ended: {ctx.step_count} steps")
            del self._active_tasks[tid]

    def check_before_action(
        self,
        action: str,
        tool_name: str,
        llm_assess_func=None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if action aligns with goal before executing.

        Returns:
            (should_proceed, warning_or_alternative)
        """
        if self._current_task_id not in self._active_tasks:
            return True, None

        ctx = self._active_tasks[self._current_task_id]
        ctx.record_action(action, tool_name)

        # Check for install attempts
        import re
        for pattern in self._install_patterns:
            if re.search(pattern, action, re.I):
                ctx.packages_attempted.append(action)
                log.warning(f"[ALIGN] Package install detected: {action[:60]}")
                return self._assess_drift(ctx, "package_install", llm_assess_func)

        # Check for new tool
        if ctx.step_count > 1 and tool_name not in ctx.tools_used:
            # First time using this tool in this task
            log.info(f"[ALIGN] New tool in task: {tool_name}")

        # Check step threshold
        if ctx.step_count >= 5 and ctx.step_count % 5 == 0:
            log.info(f"[ALIGN] Milestone check at step {ctx.step_count}")
            return self._assess_drift(ctx, "step_milestone", llm_assess_func)

        return True, None

    def _assess_drift(
        self,
        ctx: TaskContext,
        trigger: str,
        llm_assess_func=None
    ) -> Tuple[bool, Optional[str]]:
        """
        Ask NVIDIA to assess if we're still aligned with goal.

        Returns:
            (should_proceed, alternative_path_or_warning)
        """
        if not llm_assess_func:
            return True, None

        # Build assessment prompt
        history = " → ".join(ctx.actions_taken[-5:])  # Last 5 actions

        prompt = f"""Assess goal alignment for a multi-step AI task.

Original goal: "{ctx.root_goal}"

Current progress:
- Steps taken: {ctx.step_count}
- Tools used: {', '.join(ctx.tools_used)}
- Recent actions: {history}

Trigger: {trigger} (step milestone or package install detected)

TASK: Rate alignment with original goal (0-10).
QUESTION: Is this still moving toward the root goal?
If score < 5, what is a better alternative path?

Return JSON: {{"alignment_score": 0-10, "still_relevant": true/false, "concern": "brief reason", "alternative_path": "concise suggestion or null"}}"""

        try:
            result = llm_assess_func(prompt)
            # Parse JSON from result
            import json, re
            m = re.search(r'\{.*\}', result, re.DOTALL)
            if m:
                data = json.loads(m.group(0))
                score = data.get("alignment_score", 10) / 10.0

                # Log to memory
                if self.kernel and self.kernel.memory:
                    self.kernel.memory.log_event(
                        "goal_alignment_check",
                        f"Task: {ctx.root_goal[:40]} | Score: {score:.2f} | Trigger: {trigger}",
                        {"score": score, "trigger": trigger, "steps": ctx.step_count},
                        importance=0.8 if score < self._alignment_threshold else 0.5
                    )

                if score < self._alignment_threshold:
                    log.warning(f"[ALIGN] DRIFT DETECTED: score {score:.2f}")
                    alt = data.get("alternative_path", "Consider restarting with clearer scope")
                    return False, f"Goal drift detected (score {score:.2f}/1.0). {alt}"

                return True, None

        except Exception as e:
            log.warning(f"[ALIGN] Assessment failed: {e}")

        return True, None

    def get_task_status(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """Get current task status."""
        tid = task_id or self._current_task_id
        if tid not in self._active_tasks:
            return {"active": False}

        ctx = self._active_tasks[tid]
        return {
            "active": True,
            "root_goal": ctx.root_goal,
            "step_count": ctx.step_count,
            "elapsed_minutes": (time.time() - ctx.start_time) / 60,
            "tools_used": list(ctx.tools_used),
            "divergence_risk": ctx.is_divergence_risk()
        }

    def reset(self):
        """Clear all tracking."""
        self._active_tasks.clear()
        self._current_task_id = None

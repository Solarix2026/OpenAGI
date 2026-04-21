# Copyright (c) 2026 ApeironAILab
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/ApeironAILab/OpenAGI

"""
metacognition.py — Capability matrix and self-assessment

18 dimensions scored 0-5:
conversation, file_ops, persistence, memory, computer_control, browser,
vision, multi_agent, planning, metacognition, voice, google_ecosystem,
agentic_rag, thinking_mode, world_monitor, innovation, tool_invention, self_evolution

Scores updated after every tool execution based on success rate.
EvolutionEngine reads lowest-scoring dimensions to build curriculum.
"""
import json
import logging
from pathlib import Path

log = logging.getLogger("Metacognition")
MATRIX_PATH = Path("./workspace/capability_matrix.json")

DIMENSIONS = [
    "conversation", "file_ops", "persistence", "memory_rag",
    "computer_control", "browser_automation", "vision",
    "multi_agent_coordination", "strategic_planning", "metacognition",
    "voice_interface", "google_ecosystem", "agentic_workflow",
    "world_monitoring", "innovation", "tool_invention",
    "self_evolution", "proactive_initiative"
]

DEFAULT_SCORES = {d: 1.0 for d in DIMENSIONS}


class MetacognitiveEngine:
    def __init__(self, memory):
        self.memory = memory
        self._matrix = self._load()

    def _load(self) -> dict:
        try:
            return json.loads(MATRIX_PATH.read_text())
        except Exception:
            return dict(DEFAULT_SCORES)

    def _save(self):
        MATRIX_PATH.parent.mkdir(parents=True, exist_ok=True)
        MATRIX_PATH.write_text(json.dumps(self._matrix, indent=2))

    def update_capability(self, dimension: str, delta: float):
        """Adjust score for a dimension. delta: +0.1 for success, -0.1 for failure."""
        if dimension in self._matrix:
            self._matrix[dimension] = max(0.0, min(5.0, self._matrix[dimension] + delta))
            self._save()

    def get_weakest(self, n=3) -> list[tuple[str, float]]:
        """Return N lowest-scoring dimensions."""
        sorted_dims = sorted(self._matrix.items(), key=lambda x: x[1])
        return sorted_dims[:n]

    def get_score(self, dimension: str) -> float:
        return self._matrix.get(dimension, 1.0)

    def capability_report(self) -> str:
        """Human-readable capability assessment."""
        lines = ["**Capability Matrix**"]
        for dim, score in sorted(self._matrix.items(), key=lambda x: x[1]):
            bar = "▓" * int(score) + "░" * (5 - int(score))
            lines.append(f"  {dim:<25} {bar} {score:.1f}/5")
        weakest = self.get_weakest(3)
        lines.append(f"\n**Focus areas**: {', '.join(d for d, _ in weakest)}")
        return "\n".join(lines)

    def infer_dimension_from_tool(self, tool_name: str) -> str | None:
        """Map tool name to capability dimension for auto-update."""
        mapping = {
            "websearch": "world_monitoring",
            "world_events": "world_monitoring",
            "browser_navigate": "browser_automation",
            "browser_action": "browser_automation",
            "computer_click": "computer_control",
            "computer_type": "computer_control",
            "vision_analyze": "vision",
            "screenshot_action": "vision",
            "innovate": "innovation",
            "invent_tool": "tool_invention",
            "dag_execute": "agentic_workflow",
            "spawn_subagent": "multi_agent_coordination",
            "evolve": "self_evolution",
            "plan_autonomously": "strategic_planning",
        }
        for key, dim in mapping.items():
            if key in tool_name:
                return dim
        return None

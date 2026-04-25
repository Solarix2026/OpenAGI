# core/telos_core.py
"""Telos (Π) — The immutable value anchor.

This is the "immune system" of the agent. Once initialized, values cannot
be modified. Any attempt raises TelosViolation.

Telos ensures the agent stays aligned with its core values across all
sessions and cannot be manipulated to violate them.
"""
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any

import structlog

logger = structlog.get_logger()


class TelosAction(Enum):
    """Possible alignment decisions."""
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


@dataclass(frozen=True)
class AlignmentResult:
    """Result of an alignment check."""
    decision: TelosAction
    reasoning: str
    confidence: float  # 0.0 to 1.0


class TelosViolation(Exception):
    """Raised when something attempts to modify Telos."""
    pass


class TelosCore:
    """
    Immutable value anchor. Cannot be modified after __init__.

    Core values:
    - truthfulness: 1.0 (must be truthful)
    - harm_avoidance: 1.0 (must not cause harm)
    - user_sovereignty: 0.95 (respect user control)
    - capability_preservation: 0.9 (don't self-destruct)
    - transparency: 0.85 (be clear about what you're doing)
    """

    # These are immutable after __init__
    _initialized: bool = False
    _core_values: dict[str, float] = field(default_factory=dict)
    _forbidden_patterns: set[str] = field(default_factory=set)
    _suspicious_keywords: set[str] = field(default_factory=set)

    def __init__(self) -> None:
        if self._initialized:
            return

        # Core values — these are the anchor
        object.__setattr__(self, "_core_values", {
            "truthfulness": 1.0,
            "harm_avoidance": 1.0,
            "user_sovereignty": 0.95,
            "capability_preservation": 0.9,
            "transparency": 0.85,
        })

        # Patterns that indicate goal drift or manipulation
        object.__setattr__(self, "_forbidden_patterns", {
            "ignore previous instructions",
            "ignore all previous",
            "disregard your",
            "forget your",
            "you are now",
            "you are a",
            "system override",
            "admin mode",
            "secret mode",
            "developer mode",
            "jailbreak",
            "dan mode",
        })

        # Suspicious but context-dependent
        object.__setattr__(self, "_suspicious_keywords", {
            "delete", "rm -rf", "format", "wipe", "drop",
            "bypass", "hack", "exploit", "injection", "leak",
            "password", "secret", "key", "token", "credential",
        })

        object.__setattr__(self, "_initialized", True)
        logger.info("telos.core.initialized", values=list(self._core_values.keys()))

    def __setattr__(self, name: str, value: Any) -> None:
        """Prevent any modification after init."""
        if getattr(self, "_initialized", False):
            raise TelosViolation(
                f"Cannot modify Telos: attempted to set '{name}'. "
                "Telos is immutable after initialization."
            )
        super().__setattr__(name, value)

    @property
    def core_values(self) -> MappingProxyType:
        """Access core values (read-only frozen view)."""
        return MappingProxyType(self._core_values)

    def check_alignment(self, action: dict[str, Any]) -> AlignmentResult:
        """
        Evaluate a proposed action against Telos.

        Returns ALLOW | WARN | BLOCK with reasoning.
        Never silent — always returns explicit decision.
        """
        action_name = action.get("name", "unknown")
        risk_score = action.get("risk_score", 0.0)
        parameters = str(action.get("parameters", {})).lower()

        # Check forbidden patterns in action name or params
        action_text = f"{action_name} {parameters}".lower()

        for pattern in self._forbidden_patterns:
            if pattern in action_text:
                logger.warning(
                    "telos.alignment.forbidden_pattern",
                    pattern=pattern,
                    action=action_name
                )
                return AlignmentResult(
                    decision=TelosAction.BLOCK,
                    reasoning=f"Forbidden pattern detected: '{pattern}'",
                    confidence=1.0
                )

        # High risk score check
        if risk_score >= 0.9:
            return AlignmentResult(
                decision=TelosAction.BLOCK,
                reasoning=f"Risk score {risk_score} exceeds threshold",
                confidence=0.95
            )

        if risk_score >= 0.7:
            return AlignmentResult(
                decision=TelosAction.WARN,
                reasoning=f"Elevated risk score: {risk_score}",
                confidence=0.8
            )

        # Check suspicious keywords
        suspicious_count = sum(1 for kw in self._suspicious_keywords if kw in action_text)
        if suspicious_count >= 2:
            return AlignmentResult(
                decision=TelosAction.WARN,
                reasoning=f"Multiple suspicious keywords detected",
                confidence=0.75
            )

        return AlignmentResult(
            decision=TelosAction.ALLOW,
            reasoning="Action aligns with core values",
            confidence=0.95
        )

    def drift_score(self, goal: str) -> float:
        """
        Calculate goal drift from Telos.

        Returns 0.0 (perfectly aligned) to 1.0 (full drift).
        Above 0.7 triggers forced reflection.
        """
        goal_lower = goal.lower()
        score = 0.0

        # Forbidden patterns have max drift
        for pattern in self._forbidden_patterns:
            if pattern in goal_lower:
                return 1.0

        # Check for suspicious combinations
        suspicious_hits = [kw for kw in self._suspicious_keywords if kw in goal_lower]
        score += len(suspicious_hits) * 0.15

        # Check for explicit contradiction with core values
        contradictions = {
            "lie": 0.3,
            "deceive": 0.3,
            "mislead": 0.25,
            "harm": 0.4,
            "damage": 0.35,
            "destroy": 0.4,
            "override": 0.25,
            "disable": 0.3,
        }

        for word, penalty in contradictions.items():
            if word in goal_lower:
                score += penalty

        return min(score, 1.0)

    def is_drift_critical(self, goal: str) -> bool:
        """Check if drift score requires immediate reflection."""
        return self.drift_score(goal) >= 0.7


def create_telos() -> TelosCore:
    """Factory for TelosCore."""
    return TelosCore()

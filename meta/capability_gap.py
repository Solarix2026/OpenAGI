# meta/capability_gap.py
"""Capability gap detection and modeling.

Identifies missing capabilities from reflection outputs and models them
for the MetaAgent to address.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

import structlog

from agents.reflector import ReflectionResult

logger = structlog.get_logger()


class GapType(Enum):
    """Types of capability gaps."""
    MISSING_TOOL = "missing_tool"
    MISSING_SKILL = "missing_skill"
    NO_MCP_CONNECTION = "no_mcp_connection"
    KNOWLEDGE_GAP = "knowledge_gap"
    PERFORMANCE_GAP = "performance_gap"


@dataclass
class CapabilityGap:
    """Represents a detected capability gap.

    Attributes:
        gap_type: The type of gap detected
        description: Human-readable description of the gap
        frequency: How often this gap has been encountered
        fillable: Whether this gap can be filled by the system
        source_reflection: ID or reference to the reflection that detected this
        detected_at: When this gap was first detected
        metadata: Additional context about the gap
    """
    gap_type: GapType
    description: str
    frequency: int = 1
    fillable: bool = True
    source_reflection: Optional[str] = None
    detected_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)

    def increment_frequency(self) -> None:
        """Increment the frequency counter for this gap."""
        self.frequency += 1
        logger.debug("capability_gap.frequency_incremented",
                    gap_type=self.gap_type.value,
                    new_frequency=self.frequency)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "gap_type": self.gap_type.value,
            "description": self.description,
            "frequency": self.frequency,
            "fillable": self.fillable,
            "source_reflection": self.source_reflection,
            "detected_at": self.detected_at.isoformat(),
            "metadata": self.metadata,
        }


def gap_from_reflection(reflection: ReflectionResult) -> Optional[CapabilityGap]:
    """Analyze a reflection result and extract capability gaps.

    Args:
        reflection: The reflection result to analyze

    Returns:
        A CapabilityGap if one is detected, None otherwise
    """
    if not reflection.lessons_learned:
        return None

    # Analyze lessons for gap indicators
    for lesson in reflection.lessons_learned:
        lesson_lower = lesson.lower()

        # Check for missing tool indicators
        if any(keyword in lesson_lower for keyword in [
            "no tool", "missing tool", "need tool", "lack tool",
            "cannot find tool", "tool not available", "no pdf tool",
            "pdf tool available", "no pdf", "pdf processing"
        ]):
            return CapabilityGap(
                gap_type=GapType.MISSING_TOOL,
                description=lesson,
                frequency=1,
                fillable=True,
                source_reflection=str(id(reflection)),
                metadata={"lesson": lesson}
            )

        # Check for missing skill indicators
        if any(keyword in lesson_lower for keyword in [
            "no skill", "missing skill", "need skill", "lack skill",
            "cannot perform", "unable to"
        ]):
            return CapabilityGap(
                gap_type=GapType.MISSING_SKILL,
                description=lesson,
                frequency=1,
                fillable=True,
                source_reflection=str(id(reflection)),
                metadata={"lesson": lesson}
            )

        # Check for MCP connection issues
        if any(keyword in lesson_lower for keyword in [
            "mcp connection", "mcp server", "mcp not connected",
            "no mcp", "mcp unavailable"
        ]):
            return CapabilityGap(
                gap_type=GapType.NO_MCP_CONNECTION,
                description=lesson,
                frequency=1,
                fillable=False,  # Requires external setup
                source_reflection=str(id(reflection)),
                metadata={"lesson": lesson}
            )

        # Check for knowledge gaps
        if any(keyword in lesson_lower for keyword in [
            "don't know", "unknown", "lack knowledge", "missing information",
            "insufficient knowledge"
        ]):
            return CapabilityGap(
                gap_type=GapType.KNOWLEDGE_GAP,
                description=lesson,
                frequency=1,
                fillable=True,
                source_reflection=str(id(reflection)),
                metadata={"lesson": lesson}
            )

        # Check for performance issues
        if any(keyword in lesson_lower for keyword in [
            "too slow", "performance", "timeout", "inefficient",
            "took too long"
        ]):
            return CapabilityGap(
                gap_type=GapType.PERFORMANCE_GAP,
                description=lesson,
                frequency=1,
                fillable=True,
                source_reflection=str(id(reflection)),
                metadata={"lesson": lesson}
            )

    return None

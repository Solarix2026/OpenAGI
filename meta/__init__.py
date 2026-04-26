# meta/__init__.py
"""MetaAgent v2 - L3 Metacognitive Layer.

This module provides self-improvement capabilities:
- CapabilityGap: Detect missing tools, skills, and knowledge
- SkillInventor: Auto-generate tools and skills
- SelfBenchmark: Assess capability coverage
- MetaAgent: Background improvement loop with Telos gating
"""

from meta.capability_gap import CapabilityGap, GapType, gap_from_reflection
from meta.skill_inventor import SkillInventor
from meta.self_benchmark import SelfBenchmark
from meta.meta_agent_v2 import MetaAgent

__all__ = [
    "CapabilityGap",
    "GapType",
    "gap_from_reflection",
    "SkillInventor",
    "SelfBenchmark",
    "MetaAgent",
]

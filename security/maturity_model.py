# security/maturity_model.py
"""4-Stage AI Security Maturity Model.

Stage 1: Reactive    — No systematic security, ad-hoc response
Stage 2: Aware       — Asset inventory, basic policies
Stage 3: Proactive   — Continuous monitoring, threat modeling
Stage 4: Optimizing  — Automated governance, self-healing security

Based on: AI Security Governance Framework — Section 4 (Maturity Model)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from security.ai_bom import AIBOM, RiskTier
from security.shadow_detector import ShadowDetector

logger = structlog.get_logger()


class MaturityStage(Enum):
    STAGE_1_REACTIVE = 1
    STAGE_2_AWARE = 2
    STAGE_3_PROACTIVE = 3
    STAGE_4_OPTIMIZING = 4


@dataclass
class MaturityAssessment:
    stage: MaturityStage
    score: float
    strengths: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)


class AISecurityMaturityModel:
    """Assesses current AI security maturity of the OpenAGI deployment."""

    def __init__(self, bom: AIBOM, shadow_detector: ShadowDetector) -> None:
        self.bom = bom
        self.shadow_detector = shadow_detector

    def assess(self) -> MaturityAssessment:
        """Run full maturity assessment."""
        score = 0.0
        strengths = []
        gaps = []

        # Stage 1 checks (baseline)
        bom_stats = self.bom.get_stats()
        if bom_stats["total_components"] > 0:
            score += 0.25
            strengths.append("AI-BOM is populated with component inventory")
        else:
            gaps.append("AI-BOM is empty — no component tracking")

        # Stage 2 checks (aware)
        high_risk = self.bom.get_high_risk(RiskTier.TIER_3)
        if len(high_risk) == 0:
            score += 0.25
            strengths.append("No TIER_3 high-risk components present")
        else:
            gaps.append(f"{len(high_risk)} TIER_3 components present — review required")

        # Stage 3 checks (proactive)
        shadow_result = self.shadow_detector.scan()
        if shadow_result.clean:
            score += 0.25
            strengths.append("No shadow AI components detected")
        else:
            gaps.append(f"Shadow components detected: {shadow_result.shadow_tools}")

        # Stage 4 checks (optimizing)
        # Check if BOM has hash verification for all components
        all_entries = list(self.bom._entries.values())
        verified = all(e.content_hash for e in all_entries)
        if verified and all_entries:
            score += 0.25
            strengths.append("All components have content hash verification")
        else:
            gaps.append("Some components missing content hash — install verification needed")

        # Determine stage
        if score < 0.25:
            stage = MaturityStage.STAGE_1_REACTIVE
        elif score < 0.50:
            stage = MaturityStage.STAGE_2_AWARE
        elif score < 0.75:
            stage = MaturityStage.STAGE_3_PROACTIVE
        else:
            stage = MaturityStage.STAGE_4_OPTIMIZING

        return MaturityAssessment(
            stage=stage,
            score=round(score, 2),
            strengths=strengths,
            gaps=gaps,
            next_steps=self._get_next_steps(stage),
        )

    def _get_next_steps(self, stage: MaturityStage) -> list[str]:
        """Get next steps for improvement."""
        steps = {
            MaturityStage.STAGE_1_REACTIVE: [
                "Populate AI-BOM with all current components",
                "Assign risk scores to all tools and MCP connections",
            ],
            MaturityStage.STAGE_2_AWARE: [
                "Enable continuous shadow AI scanning",
                "Add content hash verification to install pipeline",
            ],
            MaturityStage.STAGE_3_PROACTIVE: [
                "Enable automated threat response for Telos violations",
                "Add supply chain verification for GitHub tool installs",
            ],
            MaturityStage.STAGE_4_OPTIMIZING: [
                "Implement automated self-healing security",
                "Enable cross-session threat correlation",
            ],
        }
        return steps.get(stage, [])

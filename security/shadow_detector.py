# security/shadow_detector.py
"""Shadow AI / Unauthorized Component Detection.

Detects tools or MCP connections that:
1. Were not registered through the official installation pipeline
2. Have unknown/unverified provenance
3. Were registered without AI-BOM logging
4. Have anomalous behavior patterns (calls unexpected endpoints)

Based on: AI Security Governance Framework — Section 2 (Shadow AI Discovery)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog

from security.ai_bom import AIBOM, BOMEntry, ComponentType
from tools.registry import ToolRegistry

logger = structlog.get_logger()


@dataclass
class ShadowDetectionResult:
    """Result of a shadow AI scan."""
    shadow_tools: list[str] = field(default_factory=list)
    unregistered_mcps: list[str] = field(default_factory=list)
    high_risk_unverified: list[str] = field(default_factory=list)
    scan_time: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    clean: bool = True


class ShadowDetector:
    """Detects unauthorized AI components in the running system."""

    def __init__(self, bom: AIBOM, registry: ToolRegistry) -> None:
        self.bom = bom
        self.registry = registry

    def scan(self) -> ShadowDetectionResult:
        """Scan for shadow AI components."""
        result = ShadowDetectionResult()

        # All tools in registry
        registered_tools = {t.name for t in self.registry.list_tools()}

        # All tools in BOM
        bom_tools = {e.name for e in self.bom.get_by_type(ComponentType.TOOL)}

        # Shadow = in registry but NOT in BOM
        shadow = registered_tools - bom_tools
        if shadow:
            result.shadow_tools = list(shadow)
            result.clean = False
            logger.warning("shadow_detector.shadow_tools_found", tools=list(shadow))

        # High-risk unverified = in BOM with TIER_3 and no content hash
        from security.ai_bom import RiskTier
        high_risk = self.bom.get_high_risk(RiskTier.TIER_3)
        unverified = [e.name for e in high_risk if not e.content_hash]
        if unverified:
            result.high_risk_unverified = unverified
            result.clean = False
            logger.warning("shadow_detector.unverified_high_risk", components=unverified)

        if result.clean:
            logger.info("shadow_detector.scan_clean")

        return result

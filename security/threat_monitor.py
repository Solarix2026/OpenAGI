# security/threat_monitor.py
"""3-Layer Threat Monitoring System.

Provides continuous monitoring for:
1. Layer 1: Component-level threats (unauthorized installations)
2. Layer 2: Behavioral threats (anomalous tool usage)
3. Layer 3: System-level threats (resource exhaustion, data exfiltration)

Based on: AI Security Governance Framework — Section 5 (Threat Monitoring)
"""
from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

import structlog

from security.ai_bom import AIBOM, RiskTier
from security.shadow_detector import ShadowDetector

logger = structlog.get_logger()


@dataclass
class ThreatEvent:
    """A detected threat event."""
    threat_type: str
    severity: str  # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    component_id: str
    description: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ThreatReport:
    """Summary of threat monitoring results."""
    total_threats: int = 0
    by_severity: dict[str, int] = field(default_factory=dict)
    by_type: dict[str, int] = field(default_factory=dict)
    recent_events: list[ThreatEvent] = field(default_factory=list)
    clean: bool = True


class ThreatMonitor:
    """3-layer threat monitoring system."""

    def __init__(
        self,
        bom: AIBOM,
        shadow_detector: ShadowDetector,
        max_events: int = 1000,
    ) -> None:
        self.bom = bom
        self.shadow_detector = shadow_detector
        self._events: deque[ThreatEvent] = deque(maxlen=max_events)
        self._tool_usage: defaultdict[str, int] = defaultdict(int)
        self._running = False

    async def start_monitoring(self, interval_seconds: int = 60) -> None:
        """Start continuous threat monitoring."""
        self._running = True
        logger.info("threat_monitor.started", interval=interval_seconds)

        while self._running:
            try:
                await self._scan_threats()
                await asyncio.sleep(interval_seconds)
            except Exception as e:
                logger.exception("threat_monitor.error", error=str(e))
                await asyncio.sleep(5)

    def stop(self) -> None:
        """Stop threat monitoring."""
        self._running = False
        logger.info("threat_monitor.stopped")

    async def _scan_threats(self) -> None:
        """Scan for threats across all layers."""
        # Layer 1: Component-level threats
        await self._scan_component_threats()

        # Layer 2: Behavioral threats
        await self._scan_behavioral_threats()

        # Layer 3: System-level threats
        await self._scan_system_threats()

    async def _scan_component_threats(self) -> None:
        """Layer 1: Scan for unauthorized components."""
        shadow_result = self.shadow_detector.scan()

        if not shadow_result.clean:
            for tool_name in shadow_result.shadow_tools:
                self._add_event(
                    threat_type="shadow_component",
                    severity="HIGH",
                    component_id=tool_name,
                    description=f"Shadow tool detected: {tool_name}",
                )

            for component_name in shadow_result.high_risk_unverified:
                self._add_event(
                    threat_type="unverified_high_risk",
                    severity="CRITICAL",
                    component_id=component_name,
                    description=f"Unverified high-risk component: {component_name}",
                )

    async def _scan_behavioral_threats(self) -> None:
        """Layer 2: Scan for anomalous behavior."""
        # Check for tools with unusually high usage
        for tool_name, count in self._tool_usage.items():
            if count > 100:  # Threshold for suspicious usage
                self._add_event(
                    threat_type="anomalous_usage",
                    severity="MEDIUM",
                    component_id=tool_name,
                    description=f"Unusually high tool usage: {tool_name} ({count} calls)",
                )

    async def _scan_system_threats(self) -> None:
        """Layer 3: Scan for system-level threats."""
        # Check for high-risk components
        high_risk = self.bom.get_high_risk(RiskTier.TIER_3)
        for entry in high_risk:
            if entry.risk.composite > 0.8:
                self._add_event(
                    threat_type="high_risk_component",
                    severity="HIGH",
                    component_id=entry.component_id,
                    description=f"High-risk component active: {entry.name} (score: {entry.risk.composite:.2f})",
                )

    def _add_event(
        self,
        threat_type: str,
        severity: str,
        component_id: str,
        description: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Add a threat event."""
        event = ThreatEvent(
            threat_type=threat_type,
            severity=severity,
            component_id=component_id,
            description=description,
            metadata=metadata or {},
        )
        self._events.append(event)
        logger.warning(
            "threat_monitor.event",
            type=threat_type,
            severity=severity,
            component=component_id,
        )

    def record_tool_usage(self, tool_name: str) -> None:
        """Record tool usage for behavioral analysis."""
        self._tool_usage[tool_name] += 1

    def get_report(self, since_hours: int = 24) -> ThreatReport:
        """Get threat report for the specified time window."""
        cutoff = datetime.utcnow() - timedelta(hours=since_hours)

        recent_events = [
            e for e in self._events
            if e.timestamp >= cutoff
        ]

        by_severity = defaultdict(int)
        by_type = defaultdict(int)

        for event in recent_events:
            by_severity[event.severity] += 1
            by_type[event.threat_type] += 1

        return ThreatReport(
            total_threats=len(recent_events),
            by_severity=dict(by_severity),
            by_type=dict(by_type),
            recent_events=list(recent_events)[-10:],  # Last 10 events
            clean=len(recent_events) == 0,
        )

    def get_events(self, limit: int = 50) -> list[ThreatEvent]:
        """Get recent threat events."""
        return list(self._events)[-limit:]

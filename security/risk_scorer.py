# security/risk_scorer.py
"""Risk Scoring — 5-dimension risk assessment for AI components.

Provides automated risk scoring based on:
1. Provenance (source verification, vendor reputation)
2. Capability (what the component can do)
3. Data Access (what data it can read/write)
4. Network Access (external service calls)
5. Drift (alignment with Telos values)

Based on: AI Security Governance Framework — Section 3 (Risk Assessment)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import structlog

from security.ai_bom import RiskScore, RiskTier

logger = structlog.get_logger()


class RiskScorer:
    """Automated risk scoring for AI components."""

    def __init__(self) -> None:
        self._risk_keywords = {
            "high": ["delete", "remove", "drop", "format", "wipe", "destroy", "kill", "terminate"],
            "medium": ["modify", "update", "change", "write", "create", "execute", "run"],
            "network": ["http", "https", "api", "fetch", "download", "upload", "connect"],
            "data": ["read", "write", "access", "export", "import", "database", "file"],
        }

    def score_from_metadata(
        self,
        metadata: dict[str, Any],
        source_url: str = "",
        content_hash: str = "",
    ) -> RiskScore:
        """Calculate risk score from component metadata."""
        provenance = self._score_provenance(source_url, content_hash)
        capability = self._score_capability(metadata)
        data_access = self._score_data_access(metadata)
        network = self._score_network(metadata)
        drift = self._score_drift(metadata)

        return RiskScore(
            provenance=provenance,
            capability=capability,
            data_access=data_access,
            network=network,
            drift=drift,
        )

    def _score_provenance(self, source_url: str, content_hash: str) -> float:
        """Score provenance risk (0=verified, 1=unknown)."""
        if not source_url:
            return 1.0  # Unknown source

        # Known trusted sources
        trusted_domains = [
            "github.com",
            "gitlab.com",
            "pypi.org",
            "npmjs.com",
            "modelcontextprotocol.io",
        ]

        if any(domain in source_url for domain in trusted_domains):
            if content_hash:
                return 0.1  # Verified source with hash
            return 0.3  # Trusted source but no hash
        else:
            return 0.8  # Unknown source

    def _score_capability(self, metadata: dict[str, Any]) -> float:
        """Score capability risk based on description and parameters."""
        description = metadata.get("description", "").lower()
        parameters = str(metadata.get("parameters", {})).lower()

        text = f"{description} {parameters}"

        # Check for high-risk keywords
        high_count = sum(1 for kw in self._risk_keywords["high"] if kw in text)
        medium_count = sum(1 for kw in self._risk_keywords["medium"] if kw in text)

        if high_count > 0:
            return 0.8 + (high_count * 0.1)
        elif medium_count > 0:
            return 0.4 + (medium_count * 0.1)
        else:
            return 0.1  # Low capability risk

    def _score_data_access(self, metadata: dict[str, Any]) -> float:
        """Score data access risk."""
        description = metadata.get("description", "").lower()
        parameters = str(metadata.get("parameters", {})).lower()

        text = f"{description} {parameters}"

        data_keywords = self._risk_keywords["data"]
        data_count = sum(1 for kw in data_keywords if kw in text)

        if data_count >= 3:
            return 0.8
        elif data_count >= 2:
            return 0.5
        elif data_count >= 1:
            return 0.3
        else:
            return 0.0

    def _score_network(self, metadata: dict[str, Any]) -> float:
        """Score network access risk."""
        description = metadata.get("description", "").lower()
        categories = metadata.get("categories", [])

        # Check for network keywords
        network_keywords = self._risk_keywords["network"]
        text = f"{description} {' '.join(categories)}"

        network_count = sum(1 for kw in network_keywords if kw in text)

        if network_count > 0:
            return 0.7
        else:
            return 0.0

    def _score_drift(self, metadata: dict[str, Any]) -> float:
        """Score drift risk (alignment with Telos)."""
        # For now, assume all components are aligned
        # In production, this would check against Telos drift detection
        return 0.0

    def get_tier_from_score(self, score: float) -> RiskTier:
        """Convert composite score to risk tier."""
        if score < 0.3:
            return RiskTier.TIER_1
        elif score < 0.6:
            return RiskTier.TIER_2
        else:
            return RiskTier.TIER_3

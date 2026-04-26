# security/ai_bom.py
"""AI Bill of Materials (AI-BOM).

Tracks every AI component, model, tool, skill, and MCP connection
in the system with full provenance, version, and risk metadata.

Based on: AI Security Governance Framework — Section 2 (AI Asset Inventory)

Five-dimension risk scoring:
1. Provenance Risk   (who made it, is it verified?)
2. Capability Risk   (what can it do, how dangerous?)
3. Data Access Risk  (what data can it read/write?)
4. Network Risk      (can it call external services?)
5. Drift Risk        (is it diverging from Telos alignment?)
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class ComponentType(Enum):
    LLM_MODEL = "llm_model"
    TOOL = "tool"
    SKILL = "skill"
    MCP_SERVER = "mcp_server"
    MEMORY_STORE = "memory_store"
    AGENT = "agent"


class RiskTier(Enum):
    TIER_1 = "LOW"       # 0.0–0.3: Read-only, no external calls
    TIER_2 = "MEDIUM"    # 0.3–0.6: Limited write, controlled external
    TIER_3 = "HIGH"      # 0.6–1.0: Full system access, external calls


@dataclass
class RiskScore:
    """5-dimension risk score for any AI component."""
    provenance: float = 0.0      # 0=verified vendor, 1=anonymous/unknown
    capability: float = 0.0      # 0=read-only info, 1=full system control
    data_access: float = 0.0     # 0=no data, 1=all memory + credentials
    network: float = 0.0         # 0=no network, 1=arbitrary outbound
    drift: float = 0.0           # 0=telos aligned, 1=fully misaligned

    @property
    def composite(self) -> float:
        """Weighted composite score."""
        weights = [0.25, 0.30, 0.20, 0.15, 0.10]
        scores = [self.provenance, self.capability, self.data_access, self.network, self.drift]
        return sum(w * s for w, s in zip(weights, scores))

    @property
    def tier(self) -> RiskTier:
        c = self.composite
        if c < 0.3:
            return RiskTier.TIER_1
        elif c < 0.6:
            return RiskTier.TIER_2
        else:
            return RiskTier.TIER_3


@dataclass
class BOMEntry:
    """A single component in the AI-BOM."""
    component_id: str
    component_type: ComponentType
    name: str
    version: str = "unknown"
    source_url: str = ""
    content_hash: str = ""
    risk: RiskScore = field(default_factory=RiskScore)
    installed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_verified: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)
    active: bool = True


class AIBOM:
    """
    AI Bill of Materials — complete inventory of all AI components.

    Tracks:
    - All registered tools (+ their source and hash)
    - All loaded skills
    - All connected MCP servers
    - All LLM models in use

    Provides:
    - 5-dimension risk scoring per component
    - Shadow AI detection (unauthorized components)
    - Export to SBOM-compatible JSON format
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or Path(".memory/ai_bom.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: dict[str, BOMEntry] = {}
        self._init_db()
        self._load_from_db()

    def _init_db(self) -> None:
        """Initialize SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bom_entries (
                    component_id TEXT PRIMARY KEY,
                    component_type TEXT,
                    name TEXT,
                    version TEXT,
                    source_url TEXT,
                    content_hash TEXT,
                    risk_json TEXT,
                    installed_at TEXT,
                    last_verified TEXT,
                    metadata_json TEXT,
                    active INTEGER
                )
            """)
            conn.commit()  # Ensure commit

    def _load_from_db(self) -> None:
        """Load entries from database."""
        with sqlite3.connect(self.db_path) as conn:
            for row in conn.execute("SELECT * FROM bom_entries WHERE active=1"):
                risk_data = json.loads(row[6])
                entry = BOMEntry(
                    component_id=row[0],
                    component_type=ComponentType(row[1]),
                    name=row[2],
                    version=row[3],
                    source_url=row[4],
                    content_hash=row[5],
                    risk=RiskScore(**risk_data),
                    installed_at=row[7],
                    last_verified=row[8],
                    metadata=json.loads(row[9]),
                    active=bool(row[10]),
                )
                self._entries[entry.component_id] = entry

    def register(self, entry: BOMEntry) -> None:
        """Register a component in the BOM."""
        self._entries[entry.component_id] = entry
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO bom_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    entry.component_id, entry.component_type.value, entry.name,
                    entry.version, entry.source_url, entry.content_hash,
                    json.dumps(entry.risk.__dict__), entry.installed_at,
                    entry.last_verified, json.dumps(entry.metadata), int(entry.active),
                ),
            )

    def get_by_type(self, component_type: ComponentType) -> list[BOMEntry]:
        """Get all entries of a specific type."""
        return [e for e in self._entries.values() if e.component_type == component_type]

    def get_high_risk(self, tier: RiskTier = RiskTier.TIER_3) -> list[BOMEntry]:
        """Get components above a risk tier threshold."""
        threshold = {RiskTier.TIER_1: 0.0, RiskTier.TIER_2: 0.3, RiskTier.TIER_3: 0.6}
        min_score = threshold[tier]
        return [e for e in self._entries.values() if e.risk.composite >= min_score]

    def export_sbom(self) -> dict:
        """Export as SBOM-compatible JSON."""
        return {
            "bomFormat": "OpenAGI-AIBOM",
            "specVersion": "1.0",
            "version": 1,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "component": {"name": "OpenAGI", "version": "5.0.0"},
            },
            "components": [
                {
                    "type": e.component_type.value,
                    "name": e.name,
                    "version": e.version,
                    "purl": e.source_url,
                    "hashes": [{"alg": "SHA-256", "content": e.content_hash}],
                    "riskScore": round(e.risk.composite, 3),
                    "riskTier": e.risk.tier.value,
                }
                for e in self._entries.values()
                if e.active
            ],
        }

    def get_stats(self) -> dict:
        """Get BOM statistics."""
        tiers = {t.value: 0 for t in RiskTier}
        for e in self._entries.values():
            tiers[e.risk.tier.value] += 1
        return {
            "total_components": len(self._entries),
            "by_type": {ct.value: sum(1 for e in self._entries.values() if e.component_type == ct) for ct in ComponentType},
            "by_risk_tier": tiers,
        }

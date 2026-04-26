# orchestrator/self_config.py
"""Self-Configuration Engine — Dynamic system optimization.

Monitors system performance, resource usage, and configuration effectiveness.
Automatically adjusts parameters to optimize performance and reliability.

Based on: OpenAGI v5 Phase 2 — L3 Self-Configuration
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import structlog

from config.settings import Settings

logger = structlog.get_logger()


class ConfigChangeType(Enum):
    """Types of configuration changes."""
    PARAMETER_ADJUSTMENT = "parameter_adjustment"
    ROUTING_CHANGE = "routing_change"
    MEMORY_TUNING = "memory_tuning"
    RESOURCE_ALLOCATION = "resource_allocation"
    MODEL_SWITCH = "model_switch"


class ConfigChangeStatus(Enum):
    """Status of configuration changes."""
    PENDING = "pending"
    APPLIED = "applied"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class SystemMetric:
    """A single system metric measurement."""
    metric_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metric_type: str = ""  # "latency", "throughput", "error_rate", "memory_usage", "cpu_usage"
    value: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfigRecommendation:
    """A recommended configuration change."""
    recommendation_id: str = field(default_factory=lambda: str(uuid4()))
    change_type: ConfigChangeType = ConfigChangeType.PARAMETER_ADJUSTMENT
    parameter_name: str = ""
    current_value: Any = None
    recommended_value: Any = None
    reason: str = ""
    confidence: float = 0.0  # 0.0 to 1.0
    estimated_impact: str = ""  # "high", "medium", "low"
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConfigChange:
    """A configuration change that was applied."""
    change_id: str = field(default_factory=lambda: str(uuid4()))
    recommendation_id: str = ""
    change_type: ConfigChangeType = ConfigChangeType.PARAMETER_ADJUSTMENT
    parameter_name: str = ""
    old_value: Any = None
    new_value: Any = None
    status: ConfigChangeStatus = ConfigChangeStatus.PENDING
    applied_at: Optional[datetime] = None
    rollback_value: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfigSnapshot:
    """A snapshot of the current configuration."""
    snapshot_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    config_json: str = ""
    metrics_summary: dict[str, float] = field(default_factory=dict)
    performance_score: float = 0.0


class SelfConfigEngine:
    """
    Self-Configuration Engine for dynamic system optimization.

    Monitors:
    - System metrics (latency, throughput, error rates)
    - Resource usage (memory, CPU)
    - Configuration effectiveness

    Provides:
    - Automatic parameter tuning
    - Configuration recommendations
    - Change tracking and rollback
    - Performance optimization
    """

    def __init__(self, settings: Settings, db_path: Optional[Path] = None) -> None:
        self.settings = settings
        self.db_path = db_path or Path(".memory/self_config.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._metrics: list[SystemMetric] = []
        self._recommendations: list[ConfigRecommendation] = []
        self._changes: list[ConfigChange] = []
        self._snapshots: list[ConfigSnapshot] = []

        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

        self._init_db()
        self._load_from_db()

    def close(self) -> None:
        """Close database connections and cleanup."""
        # SQLite connections are automatically closed when context managers exit
        # This method is for explicit cleanup if needed
        pass

    def _init_db(self) -> None:
        """Initialize SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    metric_id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    metric_type TEXT,
                    value REAL,
                    metadata_json TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recommendations (
                    recommendation_id TEXT PRIMARY KEY,
                    change_type TEXT,
                    parameter_name TEXT,
                    current_value TEXT,
                    recommended_value TEXT,
                    reason TEXT,
                    confidence REAL,
                    estimated_impact TEXT,
                    created_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS changes (
                    change_id TEXT PRIMARY KEY,
                    recommendation_id TEXT,
                    change_type TEXT,
                    parameter_name TEXT,
                    old_value TEXT,
                    new_value TEXT,
                    status TEXT,
                    applied_at TEXT,
                    rollback_value TEXT,
                    metadata_json TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    config_json TEXT,
                    metrics_summary_json TEXT,
                    performance_score REAL
                )
            """)
            conn.commit()

    def _load_from_db(self) -> None:
        """Load data from database."""
        with sqlite3.connect(self.db_path) as conn:
            # Load metrics
            for row in conn.execute("SELECT * FROM metrics ORDER BY timestamp DESC LIMIT 1000"):
                self._metrics.append(SystemMetric(
                    metric_id=row[0],
                    timestamp=datetime.fromisoformat(row[1]),
                    metric_type=row[2],
                    value=row[3],
                    metadata=json.loads(row[4]),
                ))

            # Load recommendations
            for row in conn.execute("SELECT * FROM recommendations ORDER BY created_at DESC LIMIT 100"):
                self._recommendations.append(ConfigRecommendation(
                    recommendation_id=row[0],
                    change_type=ConfigChangeType(row[1]),
                    parameter_name=row[2],
                    current_value=json.loads(row[3]) if row[3] else None,
                    recommended_value=json.loads(row[4]) if row[4] else None,
                    reason=row[5],
                    confidence=row[6],
                    estimated_impact=row[7],
                    created_at=datetime.fromisoformat(row[8]),
                ))

            # Load changes
            for row in conn.execute("SELECT * FROM changes ORDER BY applied_at DESC LIMIT 100"):
                self._changes.append(ConfigChange(
                    change_id=row[0],
                    recommendation_id=row[1],
                    change_type=ConfigChangeType(row[2]),
                    parameter_name=row[3],
                    old_value=json.loads(row[4]) if row[4] else None,
                    new_value=json.loads(row[5]) if row[5] else None,
                    status=ConfigChangeStatus(row[6]),
                    applied_at=datetime.fromisoformat(row[7]) if row[7] else None,
                    rollback_value=json.loads(row[8]) if row[8] else None,
                    metadata=json.loads(row[9]),
                ))

            # Load snapshots
            for row in conn.execute("SELECT * FROM snapshots ORDER BY timestamp DESC LIMIT 50"):
                self._snapshots.append(ConfigSnapshot(
                    snapshot_id=row[0],
                    timestamp=datetime.fromisoformat(row[1]),
                    config_json=row[2],
                    metrics_summary=json.loads(row[3]),
                    performance_score=row[4],
                ))

    def record_metric(self, metric_type: str, value: float, metadata: Optional[dict[str, Any]] = None) -> None:
        """Record a system metric."""
        metric = SystemMetric(
            metric_type=metric_type,
            value=value,
            metadata=metadata or {},
        )
        self._metrics.append(metric)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO metrics VALUES (?, ?, ?, ?, ?)",
                (
                    metric.metric_id, metric.timestamp.isoformat(),
                    metric.metric_type, metric.value,
                    json.dumps(metric.metadata),
                ),
            )
            conn.commit()

        logger.debug("self_config.metric_recorded", metric_type=metric_type, value=value)

    def analyze_metrics(self, lookback_hours: int = 24) -> dict[str, Any]:
        """Analyze metrics and identify optimization opportunities."""
        cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)
        recent_metrics = [m for m in self._metrics if m.timestamp >= cutoff]

        if not recent_metrics:
            return {"status": "insufficient_data", "recommendations": []}

        # Group by metric type
        by_type: dict[str, list[SystemMetric]] = {}
        for metric in recent_metrics:
            if metric.metric_type not in by_type:
                by_type[metric.metric_type] = []
            by_type[metric.metric_type].append(metric)

        analysis = {
            "status": "analyzed",
            "metric_count": len(recent_metrics),
            "by_type": {},
            "recommendations": [],
        }

        # Analyze each metric type
        for metric_type, metrics in by_type.items():
            values = [m.value for m in metrics]
            avg = sum(values) / len(values)
            max_val = max(values)
            min_val = min(values)

            analysis["by_type"][metric_type] = {
                "count": len(values),
                "average": avg,
                "max": max_val,
                "min": min_val,
            }

            # Generate recommendations based on thresholds
            if metric_type == "latency" and avg > 5.0:
                analysis["recommendations"].append({
                    "type": "high_latency",
                    "severity": "high" if avg > 10.0 else "medium",
                    "message": f"Average latency {avg:.2f}s exceeds threshold",
                    "suggestion": "Consider increasing max_tokens or switching to faster model",
                })

            if metric_type == "error_rate" and avg > 0.05:
                analysis["recommendations"].append({
                    "type": "high_error_rate",
                    "severity": "high" if avg > 0.1 else "medium",
                    "message": f"Error rate {avg:.2%} exceeds threshold",
                    "suggestion": "Review tool configurations and error handling",
                })

            if metric_type == "memory_usage" and avg > 0.8:
                analysis["recommendations"].append({
                    "type": "high_memory_usage",
                    "severity": "high" if avg > 0.9 else "medium",
                    "message": f"Memory usage {avg:.2%} exceeds threshold",
                    "suggestion": "Consider increasing memory capacity or reducing working TTL",
                })

        return analysis

    def generate_recommendations(self) -> list[ConfigRecommendation]:
        """Generate configuration recommendations based on analysis."""
        analysis = self.analyze_metrics()
        recommendations = []

        for rec in analysis.get("recommendations", []):
            if rec["type"] == "high_latency":
                recommendations.append(ConfigRecommendation(
                    change_type=ConfigChangeType.MODEL_SWITCH,
                    parameter_name="llm_provider",
                    current_value=self.settings.llm_provider,
                    recommended_value="groq" if self.settings.llm_provider != "groq" else "nvidia_nim",
                    reason=rec["message"],
                    confidence=0.7,
                    estimated_impact="high",
                ))

            elif rec["type"] == "high_memory_usage":
                recommendations.append(ConfigRecommendation(
                    change_type=ConfigChangeType.MEMORY_TUNING,
                    parameter_name="memory.working_ttl",
                    current_value=self.settings.memory.working_ttl,
                    recommended_value=max(1800, self.settings.memory.working_ttl - 1800),
                    reason=rec["message"],
                    confidence=0.8,
                    estimated_impact="medium",
                ))

        # Store recommendations
        for rec in recommendations:
            self._recommendations.append(rec)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO recommendations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        rec.recommendation_id, rec.change_type.value,
                        rec.parameter_name,
                        json.dumps(rec.current_value) if rec.current_value else None,
                        json.dumps(rec.recommended_value) if rec.recommended_value else None,
                        rec.reason, rec.confidence, rec.estimated_impact,
                        rec.created_at.isoformat(),
                    ),
                )
                conn.commit()

        logger.info("self_config.recommendations_generated", count=len(recommendations))
        return recommendations

    def apply_change(self, recommendation: ConfigRecommendation) -> ConfigChange:
        """Apply a configuration change."""
        change = ConfigChange(
            recommendation_id=recommendation.recommendation_id,
            change_type=recommendation.change_type,
            parameter_name=recommendation.parameter_name,
            old_value=recommendation.current_value,
            new_value=recommendation.recommended_value,
            status=ConfigChangeStatus.APPLIED,
            applied_at=datetime.utcnow(),
            rollback_value=recommendation.current_value,
        )

        # Apply the change to settings
        if recommendation.parameter_name == "llm_provider":
            self.settings.llm_provider = recommendation.recommended_value
        elif recommendation.parameter_name == "memory.working_ttl":
            self.settings.memory.working_ttl = recommendation.recommended_value

        # Store the change
        self._changes.append(change)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO changes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    change.change_id, change.recommendation_id,
                    change.change_type.value, change.parameter_name,
                    json.dumps(change.old_value) if change.old_value else None,
                    json.dumps(change.new_value) if change.new_value else None,
                    change.status.value, change.applied_at.isoformat(),
                    json.dumps(change.rollback_value) if change.rollback_value else None,
                    json.dumps(change.metadata),
                ),
            )
            conn.commit()

        logger.info("self_config.change_applied", parameter=change.parameter_name, new_value=change.new_value)
        return change

    def rollback_change(self, change_id: str) -> Optional[ConfigChange]:
        """Rollback a configuration change."""
        for change in self._changes:
            if change.change_id == change_id and change.status == ConfigChangeStatus.APPLIED:
                # Apply rollback value
                if change.parameter_name == "llm_provider":
                    self.settings.llm_provider = change.rollback_value
                elif change.parameter_name == "memory.working_ttl":
                    self.settings.memory.working_ttl = change.rollback_value

                # Update status
                change.status = ConfigChangeStatus.ROLLED_BACK

                # Update in database
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "UPDATE changes SET status = ? WHERE change_id = ?",
                        (ConfigChangeStatus.ROLLED_BACK.value, change_id),
                    )
                    conn.commit()

                logger.info("self_config.change_rolled_back", change_id=change_id)
                return change

        return None

    def create_snapshot(self) -> ConfigSnapshot:
        """Create a configuration snapshot."""
        # Calculate performance score
        analysis = self.analyze_metrics()
        performance_score = 1.0

        # Deduct points for issues
        for rec in analysis.get("recommendations", []):
            if rec["severity"] == "high":
                performance_score -= 0.2
            elif rec["severity"] == "medium":
                performance_score -= 0.1

        performance_score = max(0.0, performance_score)

        # Create snapshot
        snapshot = ConfigSnapshot(
            config_json=self.settings.model_dump_json(),
            metrics_summary=analysis.get("by_type", {}),
            performance_score=performance_score,
        )

        self._snapshots.append(snapshot)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO snapshots VALUES (?, ?, ?, ?, ?)",
                (
                    snapshot.snapshot_id, snapshot.timestamp.isoformat(),
                    snapshot.config_json, json.dumps(snapshot.metrics_summary),
                    snapshot.performance_score,
                ),
            )
            conn.commit()

        logger.info("self_config.snapshot_created", performance_score=performance_score)
        return snapshot

    async def start_monitoring(self, interval_seconds: int = 60) -> None:
        """Start background monitoring."""
        if self._running:
            return

        self._running = True

        async def monitor_loop():
            while self._running:
                try:
                    # Record synthetic metrics (in real system, these would come from actual monitoring)
                    self.record_metric("latency", 2.5 + hash(str(datetime.utcnow())) % 100 / 100.0)
                    self.record_metric("throughput", 10.0 + hash(str(datetime.utcnow())) % 50 / 10.0)
                    self.record_metric("error_rate", 0.01 + hash(str(datetime.utcnow())) % 100 / 10000.0)

                    # Analyze and generate recommendations
                    self.analyze_metrics()
                    self.generate_recommendations()

                    # Create periodic snapshot
                    if len(self._snapshots) == 0 or (datetime.utcnow() - self._snapshots[-1].timestamp) > timedelta(hours=1):
                        self.create_snapshot()

                except Exception as e:
                    logger.error("self_config.monitoring_error", error=str(e))

                await asyncio.sleep(interval_seconds)

        self._monitor_task = asyncio.create_task(monitor_loop())
        logger.info("self_config.monitoring_started", interval=interval_seconds)

    async def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("self_config.monitoring_stopped")

    def get_stats(self) -> dict[str, Any]:
        """Get self-configuration statistics."""
        return {
            "metrics_count": len(self._metrics),
            "recommendations_count": len(self._recommendations),
            "changes_count": len(self._changes),
            "snapshots_count": len(self._snapshots),
            "running": self._running,
            "latest_performance_score": self._snapshots[-1].performance_score if self._snapshots else 0.0,
        }

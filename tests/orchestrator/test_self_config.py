# tests/orchestrator/test_self_config.py
"""Tests for Self-Configuration Engine."""
import asyncio
import pytest
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from orchestrator.self_config import (
    SelfConfigEngine,
    SystemMetric,
    ConfigRecommendation,
    ConfigChange,
    ConfigSnapshot,
    ConfigChangeType,
    ConfigChangeStatus,
)
from config.settings import Settings


@pytest.fixture
def temp_db():
    """Create a temporary in-memory database for testing."""
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def temp_engine():
    """Create a temporary SelfConfigEngine for testing."""
    import tempfile
    import uuid
    # Create a unique temporary directory for each test
    tmpdir = Path(tempfile.mkdtemp())
    db_path = tmpdir / f"test_self_config_{uuid.uuid4().hex[:8]}.db"
    settings = Settings()
    engine = SelfConfigEngine(settings, db_path=db_path)
    yield engine
    # Close engine
    engine.close()
    # Cleanup
    import shutil
    try:
        shutil.rmtree(tmpdir)
    except PermissionError:
        pass  # Windows file lock issues


def test_self_config_initialization(temp_engine):
    """SelfConfigEngine initializes correctly."""
    assert temp_engine.settings is not None
    assert temp_engine.db_path.exists()
    assert len(temp_engine._metrics) == 0
    assert len(temp_engine._recommendations) == 0
    assert len(temp_engine._changes) == 0
    assert len(temp_engine._snapshots) == 0


def test_system_metric_creation(temp_db):
    """SystemMetric can be created."""
    metric = SystemMetric(
        metric_type="latency",
        value=2.5,
        metadata={"source": "test"},
    )

    assert metric.metric_type == "latency"
    assert metric.value == 2.5
    assert metric.metadata["source"] == "test"


def test_config_recommendation_creation(temp_db):
    """ConfigRecommendation can be created."""
    rec = ConfigRecommendation(
        change_type=ConfigChangeType.MODEL_SWITCH,
        parameter_name="llm_provider",
        current_value="nvidia_nim",
        recommended_value="groq",
        reason="High latency detected",
        confidence=0.8,
        estimated_impact="high",
    )

    assert rec.change_type == ConfigChangeType.MODEL_SWITCH
    assert rec.parameter_name == "llm_provider"
    assert rec.confidence == 0.8
    assert rec.estimated_impact == "high"


def test_config_change_creation(temp_db):
    """ConfigChange can be created."""
    change = ConfigChange(
        recommendation_id="test-rec-1",
        change_type=ConfigChangeType.PARAMETER_ADJUSTMENT,
        parameter_name="memory.working_ttl",
        old_value=3600,
        new_value=1800,
        status=ConfigChangeStatus.APPLIED,
        rollback_value=3600,
    )

    assert change.recommendation_id == "test-rec-1"
    assert change.change_type == ConfigChangeType.PARAMETER_ADJUSTMENT
    assert change.old_value == 3600
    assert change.new_value == 1800
    assert change.status == ConfigChangeStatus.APPLIED


def test_config_snapshot_creation(temp_db):
    """ConfigSnapshot can be created."""
    snapshot = ConfigSnapshot(
        config_json='{"test": "value"}',
        metrics_summary={"latency": 2.5},
        performance_score=0.9,
    )

    assert snapshot.config_json == '{"test": "value"}'
    assert snapshot.metrics_summary["latency"] == 2.5
    assert snapshot.performance_score == 0.9


def test_self_config_records_metric(temp_engine):
    """SelfConfigEngine can record metrics."""
    temp_engine.record_metric("latency", 2.5, {"source": "test"})

    assert len(temp_engine._metrics) == 1
    assert temp_engine._metrics[0].metric_type == "latency"
    assert temp_engine._metrics[0].value == 2.5
    assert temp_engine._metrics[0].metadata["source"] == "test"


def test_self_config_records_multiple_metrics(temp_engine):
    """SelfConfigEngine can record multiple metrics."""
    temp_engine.record_metric("latency", 2.5)
    temp_engine.record_metric("throughput", 10.0)
    temp_engine.record_metric("error_rate", 0.01)

    assert len(temp_engine._metrics) == 3
    assert any(m.metric_type == "latency" for m in temp_engine._metrics)
    assert any(m.metric_type == "throughput" for m in temp_engine._metrics)
    assert any(m.metric_type == "error_rate" for m in temp_engine._metrics)


def test_self_config_analyzes_metrics(temp_engine):
    """SelfConfigEngine can analyze metrics."""
    # Record some metrics
    temp_engine.record_metric("latency", 2.5)
    temp_engine.record_metric("latency", 3.0)
    temp_engine.record_metric("latency", 2.8)

    analysis = temp_engine.analyze_metrics()

    assert analysis["status"] == "analyzed"
    assert analysis["metric_count"] == 3
    assert "latency" in analysis["by_type"]
    assert analysis["by_type"]["latency"]["count"] == 3
    assert 2.7 <= analysis["by_type"]["latency"]["average"] <= 2.8


def test_self_config_generates_latency_recommendations(temp_engine):
    """SelfConfigEngine generates recommendations for high latency."""
    # Record high latency metrics
    for _ in range(10):
        temp_engine.record_metric("latency", 6.0 + hash(str(datetime.utcnow())) % 100 / 100.0)

    recommendations = temp_engine.generate_recommendations()

    assert len(recommendations) >= 1
    assert any(r.change_type == ConfigChangeType.MODEL_SWITCH for r in recommendations)


def test_self_config_generates_memory_recommendations(temp_engine):
    """SelfConfigEngine generates recommendations for high memory usage."""
    # Record high memory usage metrics
    for _ in range(10):
        temp_engine.record_metric("memory_usage", 0.85 + hash(str(datetime.utcnow())) % 100 / 1000.0)

    recommendations = temp_engine.generate_recommendations()

    assert len(recommendations) >= 1
    assert any(r.change_type == ConfigChangeType.MEMORY_TUNING for r in recommendations)


def test_self_config_applies_change(temp_engine):
    """SelfConfigEngine can apply configuration changes."""
    # Create a recommendation
    rec = ConfigRecommendation(
        change_type=ConfigChangeType.MODEL_SWITCH,
        parameter_name="llm_provider",
        current_value="nvidia_nim",
        recommended_value="groq",
        reason="Test",
        confidence=0.8,
        estimated_impact="medium",
    )

    change = temp_engine.apply_change(rec)

    assert change.status == ConfigChangeStatus.APPLIED
    assert change.new_value == "groq"
    assert change.rollback_value == "nvidia_nim"
    assert len(temp_engine._changes) == 1


def test_self_config_rolls_back_change(temp_engine):
    """SelfConfigEngine can rollback configuration changes."""
    # Create and apply a change
    rec = ConfigRecommendation(
        change_type=ConfigChangeType.MODEL_SWITCH,
        parameter_name="llm_provider",
        current_value="nvidia_nim",
        recommended_value="groq",
        reason="Test",
        confidence=0.8,
        estimated_impact="medium",
    )

    change = temp_engine.apply_change(rec)
    assert change.status == ConfigChangeStatus.APPLIED

    # Rollback
    rolled_back = temp_engine.rollback_change(change.change_id)

    assert rolled_back is not None
    assert rolled_back.status == ConfigChangeStatus.ROLLED_BACK
    assert temp_engine.settings.llm_provider == "nvidia_nim"


def test_self_config_creates_snapshot(temp_engine):
    """SelfConfigEngine can create configuration snapshots."""
    # Record some metrics
    temp_engine.record_metric("latency", 2.5)
    temp_engine.record_metric("throughput", 10.0)

    snapshot = temp_engine.create_snapshot()

    assert snapshot.config_json is not None
    assert len(snapshot.metrics_summary) > 0
    assert 0.0 <= snapshot.performance_score <= 1.0
    assert len(temp_engine._snapshots) == 1


def test_self_config_calculates_performance_score(temp_engine):
    """SelfConfigEngine calculates performance score correctly."""
    # Record good metrics
    for _ in range(5):
        temp_engine.record_metric("latency", 2.0)
        temp_engine.record_metric("error_rate", 0.01)

    snapshot = temp_engine.create_snapshot()

    # Should have high performance score
    assert snapshot.performance_score >= 0.9


def test_self_config_calculates_low_performance_score(temp_engine):
    """SelfConfigEngine calculates low performance score for bad metrics."""
    # Record bad metrics
    for _ in range(5):
        temp_engine.record_metric("latency", 12.0)  # High latency
        temp_engine.record_metric("error_rate", 0.15)  # High error rate

    snapshot = temp_engine.create_snapshot()

    # Should have lower performance score
    assert snapshot.performance_score < 0.8


def test_self_config_gets_stats(temp_engine):
    """SelfConfigEngine can provide statistics."""
    # Add some data
    temp_engine.record_metric("latency", 2.5)
    temp_engine.record_metric("throughput", 10.0)

    rec = ConfigRecommendation(
        change_type=ConfigChangeType.MODEL_SWITCH,
        parameter_name="llm_provider",
        current_value="nvidia_nim",
        recommended_value="groq",
        reason="Test",
        confidence=0.8,
        estimated_impact="medium",
    )
    temp_engine.apply_change(rec)

    temp_engine.create_snapshot()

    stats = temp_engine.get_stats()

    assert stats["metrics_count"] >= 2
    assert stats["changes_count"] >= 1
    assert stats["snapshots_count"] >= 1
    assert stats["running"] is False


@pytest.mark.asyncio
async def test_self_config_starts_monitoring(temp_engine):
    """SelfConfigEngine can start background monitoring."""
    await temp_engine.start_monitoring(interval_seconds=1)

    assert temp_engine._running is True
    assert temp_engine._monitor_task is not None

    # Wait a bit for monitoring to run
    await asyncio.sleep(2)

    # Should have recorded some metrics
    assert len(temp_engine._metrics) > 0

    await temp_engine.stop()


@pytest.mark.asyncio
async def test_self_config_stops_monitoring(temp_engine):
    """SelfConfigEngine can stop background monitoring."""
    await temp_engine.start_monitoring(interval_seconds=1)
    assert temp_engine._running is True

    await temp_engine.stop()

    assert temp_engine._running is False


def test_self_config_persists_to_database(temp_engine):
    """SelfConfigEngine persists data to database."""
    # Record metric
    temp_engine.record_metric("latency", 2.5)

    # Create new engine with same db path
    settings = Settings()
    engine2 = SelfConfigEngine(settings, db_path=temp_engine.db_path)

    # Should have loaded the metric
    assert len(engine2._metrics) >= 1
    assert any(m.metric_type == "latency" for m in engine2._metrics)


def test_self_config_handles_insufficient_data(temp_engine):
    """SelfConfigEngine handles insufficient data gracefully."""
    # No metrics recorded
    analysis = temp_engine.analyze_metrics()

    assert analysis["status"] == "insufficient_data"
    assert analysis["recommendations"] == []


def test_self_config_filters_by_time(temp_engine):
    """SelfConfigEngine filters metrics by time window."""
    # Record old metric
    old_metric = SystemMetric(
        metric_type="latency",
        value=2.5,
        timestamp=datetime.utcnow() - timedelta(hours=25),
    )
    temp_engine._metrics.append(old_metric)

    # Record recent metric
    temp_engine.record_metric("latency", 3.0)

    analysis = temp_engine.analyze_metrics(lookback_hours=24)

    # Should only include recent metric
    assert analysis["metric_count"] == 1
    assert analysis["by_type"]["latency"]["average"] == 3.0

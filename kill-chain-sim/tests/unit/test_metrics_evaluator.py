import pytest
from metrics_evaluator import (
    MetricsEvaluator, MetricsSummary, MetricCategory,
    TrackEvent, AllocationEvent, EngagementResult,
    evaluate_from_logs
)
import time


def test_track_continuity_score():
    """Test track continuity evaluation."""
    evaluator = MetricsEvaluator()
    now = time.time()
    
    # Track 1: Complete lifecycle
    tracks = [
        TrackEvent(1, "created", now - 100, 30.0, 120.0, 10000),
        TrackEvent(1, "updated", now - 50, 30.5, 120.5, 11000),
        TrackEvent(1, "killed", now - 10, 31.0, 121.0, 12000),  # 90 sec duration
    ]
    
    summary = evaluator.evaluate(tracks, [], [])
    
    # Track lasted 90 sec, should score well
    assert summary.track_continuity_score > 50
    assert len(summary.per_metric_results) == 5


def test_allocation_efficiency_scoring():
    """Test allocation efficiency calculation."""
    evaluator = MetricsEvaluator()
    now = time.time()
    
    allocations = [
        AllocationEvent(1, 101, 201, 3.0, 0.9, 12.0, now - 50),  # Fast, high priority
        AllocationEvent(2, 102, 202, 5.0, 0.7, 20.0, now - 40),
    ]
    
    summary = evaluator.evaluate([], allocations, [])
    
    # Fast decisions should give high score
    assert summary.allocation_efficiency_score > 60


def test_engagement_effectiveness():
    """Test engagement effectiveness evaluation."""
    evaluator = MetricsEvaluator()
    now = time.time()
    
    engagements = [
        EngagementResult(1, 201, 15.0, 0.85, "killed", now - 10),
        EngagementResult(2, 202, 20.0, 0.7, "killed", now - 15),
        EngagementResult(3, 203, 25.0, 0.6, "escaped", now - 20),  # Bad
    ]
    
    summary = evaluator.evaluate([], [], engagements)
    
    # 2/3 killed = 66%, minus escape penalty
    assert 50 < summary.engagement_effectiveness_score < 80


def test_ooda_loop_speed():
    """Test OODA loop evaluation."""
    evaluator = MetricsEvaluator()
    now = time.time()
    
    allocations = [
        AllocationEvent(1, 101, 201, 8.0, 0.8, 20.0, now - 50),  # 8 sec OODA
        AllocationEvent(2, 102, 202, 12.0, 0.7, 25.0, now - 40),  # 12 sec OODA
    ]
    
    summary = evaluator.evaluate([], allocations, [])
    
    # Average 10 sec - should score around 60-80
    assert 50 < summary.ooda_loop_score < 90


def test_no_data_returns_zero():
    """Test with empty data."""
    evaluator = MetricsEvaluator()
    
    summary = evaluator.evaluate([], [], [])
    
    assert summary.composite_score == 0.0
    assert len(summary.per_metric_results) == 5


def test_coverage_default():
    """Test coverage with no grid data."""
    evaluator = MetricsEvaluator()
    
    summary = evaluator.evaluate([], [], [])
    
    # No coverage data should give neutral score
    assert summary.coverage_score == 50.0


def test_composite_score_calculation():
    """Test composite score weighting."""
    evaluator = MetricsEvaluator(weights={
        "track_continuity": 0.5,  # High weight
        "allocation_efficiency": 0.2,
        "engagement_effectiveness": 0.2,
        "ooda_loop": 0.05,
        "coverage": 0.05
    })
    now = time.time()
    
    tracks = [
        TrackEvent(1, "created", now - 100, 30.0, 120.0, 10000),
        TrackEvent(1, "killed", now - 10, 31.0, 121.0, 12000),
    ]
    
    allocations = [
        AllocationEvent(1, 101, 201, 3.0, 0.9, 15.0, now - 95),
    ]
    
    engagements = [
        EngagementResult(1, 201, 15.0, 0.85, "killed", now - 5),
    ]
    
    summary = evaluator.evaluate(tracks, allocations, engagements)
    
    # Composite should be dominated by track_continuity (50%)
    # Expected: 0.5 * tc_score + 0.2 * ae_score + 0.2 * ee_score + ...
    assert 0 <= summary.composite_score <= 100
    # With high weights, if track is good, composite should reflect that
    assert summary.composite_score > 20


def test_evaluate_from_logs():
    """Test convenience function with dict data."""
    import time
    now = time.time()
    
    track_log = [
        {"track_id": 1, "event_type": "created", "timestamp": now - 100, 
         "lat": 30.0, "lon": 120.0, "alt": 10000},
        {"track_id": 1, "event_type": "killed", "timestamp": now - 10,
         "lat": 31.0, "lon": 121.0, "alt": 12000},
    ]
    
    allocation_log = [
        {"target_id": 1, "sensor_id": 101, "weapon_id": 201, 
         "decision_time": 3.0, "priority_score": 0.9, "intercept_time": 15.0,
         "timestamp": now - 95}
    ]
    
    engagement_log = [
        {"target_id": 1, "weapon_id": 201, "intercept_time": 15.0,
         "p_kill_actual": 0.85, "outcome": "killed", "timestamp": now - 5}
    ]
    
    summary = evaluate_from_logs(track_log, allocation_log, engagement_log)
    
    assert isinstance(summary, MetricsSummary)
    assert summary.composite_score >= 0
    assert len(summary.per_metric_results) == 5


def test_all_metrics_present():
    """Test all metric categories are computed."""
    evaluator = MetricsEvaluator()
    now = time.time()
    
    tracks = [TrackEvent(1, "created", now - 100, 30.0, 120.0, 10000)]
    allocations = [AllocationEvent(1, 101, 201, 5.0, 0.8, 20.0, now - 95)]
    engagements = [EngagementResult(1, 201, 20.0, 0.8, "killed", now - 10)]
    
    summary = evaluator.evaluate(tracks, allocations, engagements)
    
    metric_names = {m.name for m in summary.per_metric_results}
    expected = {"track_continuity", "allocation_efficiency", "engagement_effectiveness", 
               "ooda_loop", "coverage"}
    assert expected.issubset(metric_names)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
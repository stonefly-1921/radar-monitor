"""
Kill Chain Metrics Evaluator - Multi-Objective Performance Assessment

Evaluates kill chain effectiveness across multiple dimensions:
1. Track Continuity - How well do we maintain track on targets?
2. Allocation Efficiency - How optimally are resources allocated?
3. Engagement Effectiveness - How well do engagements neutralize threats?
4. OODA Loop Speed - How fast is the observe-orient-decide-act cycle?
5. Coverage - How well do sensors cover the battlespace?

Usage:
    evaluator = MetricsEvaluator()
    metrics = evaluator.evaluate(session_data, allocation_results, engagement_log)
    score = evaluator.composite_score(metrics)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import math
import time


class MetricCategory(Enum):
    TRACKING = "tracking"
    ALLOCATION = "allocation"
    ENGAGEMENT = "engagement"
    OODA = "ooda"
    COVERAGE = "coverage"


@dataclass
class MetricResult:
    """Result for a single metric."""
    name: str
    category: MetricCategory
    value: float  # Raw value
    normalized_score: float  # 0-100 score
    weight: float  # Contribution to composite score
    details: Dict = field(default_factory=dict)
    
    def __repr__(self):
        return f"{self.name}: {self.normalized_score:.1f}/100 (raw={self.value:.2f})"


@dataclass
class MetricsSummary:
    """Complete metrics summary."""
    track_continuity_score: float  # 0-100
    allocation_efficiency_score: float
    engagement_effectiveness_score: float
    ooda_loop_score: float
    coverage_score: float
    composite_score: float  # Weighted combination
    
    per_metric_results: List[MetricResult] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            "track_continuity": self.track_continuity_score,
            "allocation_efficiency": self.allocation_efficiency_score,
            "engagement_effectiveness": self.engagement_effectiveness_score,
            "ooda_loop": self.ooda_loop_score,
            "coverage": self.coverage_score,
            "composite": self.composite_score,
            "timestamp": self.timestamp
        }


@dataclass 
class TrackEvent:
    """Track lifecycle event."""
    track_id: int
    event_type: str  # "created", "updated", "lost", "engaged", "killed"
    timestamp: float
    lat: float = 0.0
    lon: float = 0.0
    alt: float = 0.0


@dataclass
class AllocationEvent:
    """Allocation decision event."""
    target_id: int
    sensor_id: int
    weapon_id: int
    decision_time_sec: float  # Time from track creation to allocation
    priority_score: float
    intercept_time_sec: float
    timestamp: float


@dataclass
class EngagementResult:
    """Engagement outcome."""
    target_id: int
    weapon_id: int
    intercept_time_sec: float
    p_kill_actual: float  # Actual PK achieved
    outcome: str  # "killed", "escaped", "neutralized", "failed"
    timestamp: float


class MetricsEvaluator:
    """
    Multi-objective metrics evaluator for kill chain performance.
    
    Weights (configurable):
        Track Continuity: 0.20
        Allocation Efficiency: 0.25
        Engagement Effectiveness: 0.30
        OODA Loop Speed: 0.15
        Coverage: 0.10
    """
    
    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        track_continuity_target_sec: float = 2.0,
        max_ooda_time_sec: float = 30.0
    ):
        # Default weights
        self.weights = weights or {
            "track_continuity": 0.20,
            "allocation_efficiency": 0.25,
            "engagement_effectiveness": 0.30,
            "ooda_loop": 0.15,
            "coverage": 0.10
        }
        
        # Thresholds
        self.track_continuity_target = track_continuity_target_sec
        self.max_ooda_time = max_ooda_time_sec
        
    def evaluate(
        self,
        track_events: List[TrackEvent],
        allocations: List[AllocationEvent],
        engagements: List[EngagementResult],
        coverage_grid: Optional[Dict[Tuple[int, int], float]] = None
    ) -> MetricsSummary:
        """
        Evaluate kill chain performance.
        
        Args:
            track_events: List of track lifecycle events
            allocations: List of allocation decisions
            engagements: List of engagement outcomes
            coverage_grid: Optional grid of coverage (lat_idx, lon_idx) -> coverage_factor
            
        Returns:
            MetricsSummary with scores
        """
        results = []
        
        # 1. Track Continuity
        tc_result = self._eval_track_continuity(track_events)
        results.append(tc_result)
        
        # 2. Allocation Efficiency
        ae_result = self._eval_allocation_efficiency(allocations)
        results.append(ae_result)
        
        # 3. Engagement Effectiveness
        ee_result = self._eval_engagement_effectiveness(engagements)
        results.append(ee_result)
        
        # 4. OODA Loop Speed
        ooda_result = self._eval_ooda_loop(allocations, track_events)
        results.append(ooda_result)
        
        # 5. Coverage
        cov_result = self._eval_coverage(coverage_grid)
        results.append(cov_result)
        
        # Calculate composite
        composite = sum(r.normalized_score * self.weights.get(r.name, 0.2) 
                      for r in results)
        
        return MetricsSummary(
            track_continuity_score=tc_result.normalized_score,
            allocation_efficiency_score=ae_result.normalized_score,
            engagement_effectiveness_score=ee_result.normalized_score,
            ooda_loop_score=ooda_result.normalized_score,
            coverage_score=cov_result.normalized_score,
            composite_score=composite,
            per_metric_results=results
        )
    
    def _eval_track_continuity(self, events: List[TrackEvent]) -> MetricResult:
        """Evaluate how well tracks are maintained."""
        if not events:
            return MetricResult(
                "track_continuity", MetricCategory.TRACKING, 0.0, 0.0, 
                self.weights["track_continuity"]
            )
        
        # Calculate track lifetime statistics
        track_durations = {}
        track_loss_count = 0
        
        # Sort by time
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        
        for event in sorted_events:
            if event.event_type == "created":
                track_durations[event.track_id] = {"start": event.timestamp, "end": None}
            elif event.event_type == "lost":
                if event.track_id in track_durations:
                    track_durations[event.track_id]["end"] = event.timestamp
                    track_loss_count += 1
            elif event.event_type == "killed":
                if event.track_id in track_durations:
                    track_durations[event.track_id]["end"] = event.timestamp
        
        # Calculate average track duration
        durations = []
        for tid, d in track_durations.items():
            if d["end"] is not None:
                durations.append(d["end"] - d["start"])
        
        if not durations:
            avg_duration = 0.0
            continuity_ratio = 0.0
        else:
            avg_duration = sum(durations) / len(durations)
            # Continuity ratio: tracks that completed vs tracks lost early
            completed = sum(1 for d in durations if d > self.track_continuity_target)
            continuity_ratio = completed / len(durations) if durations else 0.0
        
        # Normalize to 0-100
        # Duration score: 2 min = 100, 10 sec = 0
        duration_score = min(100, (avg_duration / 120.0) * 100) if avg_duration > 0 else 0
        
        # Loss penalty
        loss_penalty = min(30, track_loss_count * 10)
        
        raw_value = avg_duration
        normalized = max(0, min(100, duration_score - loss_penalty))
        
        return MetricResult(
            "track_continuity",
            MetricCategory.TRACKING,
            raw_value,
            normalized,
            self.weights["track_continuity"],
            {
                "avg_duration_sec": avg_duration,
                "tracks_completed": len(durations),
                "tracks_lost": track_loss_count,
                "continuity_ratio": continuity_ratio
            }
        )
    
    def _eval_allocation_efficiency(self, allocations: List[AllocationEvent]) -> MetricResult:
        """Evaluate allocation algorithm efficiency."""
        if not allocations:
            return MetricResult(
                "allocation_efficiency", MetricCategory.ALLOCATION, 0.0, 0.0,
                self.weights["allocation_efficiency"]
            )
        
        # Metrics:
        # 1. Decision time (faster is better)
        # 2. Priority score distribution (higher is better)
        # 3. Intercept time (shorter is better)
        
        decision_times = [a.decision_time_sec for a in allocations]
        priority_scores = [a.priority_score for a in allocations]
        intercept_times = [a.intercept_time_sec for a in allocations]
        
        avg_decision_time = sum(decision_times) / len(decision_times)
        avg_priority = sum(priority_scores) / len(priority_scores)
        avg_intercept = sum(intercept_times) / len(intercept_times)
        
        # Score components
        # Decision time: <2 sec = 100, >20 sec = 0
        dt_score = max(0, min(100, (20 - avg_decision_time) / 18 * 100))
        
        # Priority score: normalized already (0-1)
        priority_score_norm = avg_priority * 100  # Convert to 0-100
        
        # Intercept time: <10 sec = 100, >120 sec = 0
        intercept_score = max(0, min(100, (120 - avg_intercept) / 110 * 100))
        
        # Combined (weighted)
        combined = dt_score * 0.3 + priority_score_norm * 0.4 + intercept_score * 0.3
        
        return MetricResult(
            "allocation_efficiency",
            MetricCategory.ALLOCATION,
            avg_decision_time,
            combined,
            self.weights["allocation_efficiency"],
            {
                "avg_decision_time_sec": avg_decision_time,
                "avg_priority_score": avg_priority,
                "avg_intercept_time_sec": avg_intercept,
                "num_allocations": len(allocations)
            }
        )
    
    def _eval_engagement_effectiveness(self, engagements: List[EngagementResult]) -> MetricResult:
        """Evaluate engagement outcomes."""
        if not engagements:
            return MetricResult(
                "engagement_effectiveness", MetricCategory.ENGAGEMENT, 0.0, 0.0,
                self.weights["engagement_effectiveness"]
            )
        
        killed = sum(1 for e in engagements if e.outcome == "killed")
        neutralized = sum(1 for e in engagements if e.outcome == "neutralized")
        escaped = sum(1 for e in engagements if e.outcome == "escaped")
        failed = sum(1 for e in engagements if e.outcome == "failed")
        
        total = len(engagements)
        
        # Kill ratio
        kill_ratio = killed / total if total > 0 else 0
        
        # Effective kills (killed + neutralized)
        effective_ratio = (killed + neutralized) / total if total > 0 else 0
        
        # Escape penalty
        escape_penalty = (escaped / total) * 20 if total > 0 else 0
        
        # Score
        raw_value = kill_ratio
        normalized = max(0, min(100, effective_ratio * 100 - escape_penalty))
        
        return MetricResult(
            "engagement_effectiveness",
            MetricCategory.ENGAGEMENT,
            raw_value,
            normalized,
            self.weights["engagement_effectiveness"],
            {
                "killed": killed,
                "neutralized": neutralized,
                "escaped": escaped,
                "failed": failed,
                "kill_ratio": kill_ratio,
                "total_engagements": total
            }
        )
    
    def _eval_ooda_loop(self, allocations: List[AllocationEvent], 
                        tracks: List[TrackEvent]) -> MetricResult:
        """Evaluate OODA loop speed."""
        if not allocations:
            return MetricResult(
                "ooda_loop", MetricCategory.OODA, 0.0, 0.0,
                self.weights["ooda_loop"]
            )
        
        decision_times = [a.decision_time_sec for a in allocations]
        avg_ooda_time = sum(decision_times) / len(decision_times)
        
        # Score: <5 sec = 100, >30 sec = 0
        normalized = max(0, min(100, (self.max_ooda_time - avg_ooda_time) / 
                                  (self.max_ooda_time - 5) * 100))
        
        return MetricResult(
            "ooda_loop",
            MetricCategory.OODA,
            avg_ooda_time,
            normalized,
            self.weights["ooda_loop"],
            {
                "avg_ooda_time_sec": avg_ooda_time,
                "min_time": min(decision_times) if decision_times else 0,
                "max_time": max(decision_times) if decision_times else 0
            }
        )
    
    def _eval_coverage(self, coverage_grid: Optional[Dict[Tuple[int, int], float]]) -> MetricResult:
        """Evaluate sensor coverage of battlespace."""
        if not coverage_grid:
            # No coverage data - assume neutral
            return MetricResult(
                "coverage", MetricCategory.COVERAGE, 0.5, 50.0,
                self.weights["coverage"],
                {"note": "No coverage data provided"}
            )
        
        coverage_values = list(coverage_grid.values())
        avg_coverage = sum(coverage_values) / len(coverage_values) if coverage_values else 0
        
        # Also consider high-coverage areas
        high_coverage = sum(1 for v in coverage_values if v > 0.8)
        high_coverage_ratio = high_coverage / len(coverage_values) if coverage_values else 0
        
        # Score: average + bonus for high-coverage areas
        normalized = min(100, avg_coverage * 100 + high_coverage_ratio * 20)
        
        return MetricResult(
            "coverage",
            MetricCategory.COVERAGE,
            avg_coverage,
            normalized,
            self.weights["coverage"],
            {
                "avg_coverage": avg_coverage,
                "high_coverage_cells": high_coverage,
                "total_cells": len(coverage_values)
            }
        )
    
    def print_summary(self, summary: MetricsSummary) -> str:
        """Generate human-readable summary."""
        lines = [
            "=" * 50,
            "KILL CHAIN METRICS SUMMARY",
            "=" * 50,
            f"Composite Score: {summary.composite_score:.1f}/100",
            "-" * 50,
            "Category Scores:",
            f"  Track Continuity:     {summary.track_continuity_score:.1f}/100",
            f"  Allocation Efficiency:{summary.allocation_efficiency_score:.1f}/100",
            f"  Engagement Effect.:   {summary.engagement_effectiveness_score:.1f}/100",
            f"  OODA Loop Speed:      {summary.ooda_loop_score:.1f}/100",
            f"  Coverage:            {summary.coverage_score:.1f}/100",
            "-" * 50,
            "Detailed Metrics:"
        ]
        
        for metric in summary.per_metric_results:
            lines.append(f"  [{metric.category.value.upper()}] {metric.name}")
            lines.append(f"    Score: {metric.normalized_score:.1f}/100")
            for key, value in metric.details.items():
                lines.append(f"    {key}: {value}")
        
        lines.append("=" * 50)
        return "\n".join(lines)


def evaluate_from_logs(
    track_log: List[Dict],
    allocation_log: List[Dict],
    engagement_log: List[Dict],
    coverage_grid: Optional[Dict] = None
) -> MetricsSummary:
    """
    Convenience function to evaluate from log data.
    
    Args:
        track_log: List of dicts with keys: track_id, event_type, timestamp, lat, lon, alt
        allocation_log: List of dicts with keys: target_id, sensor_id, weapon_id, decision_time, priority_score, intercept_time, timestamp
        engagement_log: List of dicts with keys: target_id, weapon_id, intercept_time, p_kill_actual, outcome, timestamp
        coverage_grid: Optional {(lat_idx, lon_idx): coverage_factor}
    
    Returns:
        MetricsSummary
    """
    # Convert to event objects
    tracks = [
        TrackEvent(
            track_id=t["track_id"],
            event_type=t["event_type"],
            timestamp=t["timestamp"],
            lat=t.get("lat", 0),
            lon=t.get("lon", 0),
            alt=t.get("alt", 0)
        )
        for t in track_log
    ]
    
    allocations = [
        AllocationEvent(
            target_id=a["target_id"],
            sensor_id=a["sensor_id"],
            weapon_id=a["weapon_id"],
            decision_time_sec=a.get("decision_time", 5.0),
            priority_score=a.get("priority_score", 0.5),
            intercept_time_sec=a.get("intercept_time", 30.0),
            timestamp=a.get("timestamp", time.time())
        )
        for a in allocation_log
    ]
    
    engagements = [
        EngagementResult(
            target_id=e["target_id"],
            weapon_id=e["weapon_id"],
            intercept_time_sec=e.get("intercept_time", 30.0),
            p_kill_actual=e.get("p_kill_actual", 0.8),
            outcome=e["outcome"],
            timestamp=e.get("timestamp", time.time())
        )
        for e in engagement_log
    ]
    
    evaluator = MetricsEvaluator()
    return evaluator.evaluate(tracks, allocations, engagements, coverage_grid)


if __name__ == "__main__":
    # Simple test
    import time
    
    now = time.time()
    
    track_events = [
        TrackEvent(1, "created", now - 100, 30.0, 120.0, 10000),
        TrackEvent(1, "updated", now - 90, 30.1, 120.1, 10500),
        TrackEvent(1, "updated", now - 60, 30.2, 120.2, 11000),
        TrackEvent(1, "killed", now - 30, 30.5, 120.5, 12000),
        TrackEvent(2, "created", now - 80, 31.0, 121.0, 8000),
        TrackEvent(2, "lost", now - 40, 31.5, 121.5, 8500),  # Lost track
    ]
    
    allocations = [
        AllocationEvent(1, 101, 201, 3.5, 0.85, 15.0, now - 95),
        AllocationEvent(2, 102, 202, 8.2, 0.72, 22.0, now - 75),
    ]
    
    engagements = [
        EngagementResult(1, 201, 15.0, 0.85, "killed", now - 25),
        EngagementResult(2, 202, 22.0, 0.72, "escaped", now - 35),  # Track lost before engagement
    ]
    
    evaluator = MetricsEvaluator()
    summary = evaluator.evaluate(track_events, allocations, engagements)
    
    print(evaluator.print_summary(summary))
    print(f"\nJSON output: {summary.to_dict()}")
"""
Kill Chain Integration Test - Full End-to-End Flow

This test demonstrates the complete kill chain management pipeline:
1. Track data generation (simulated)
2. Allocations computed (Munkres → Greedy → MILP)
3. Metrics evaluated end-to-end

Run: python -m tests.integration.test_kill_chain_flow
"""

import sys
import os
import time
import math

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from research.algorithms.milp_allocator import (
    MilpAllocator, Target, Sensor, Weapon, 
    Allocation, SolveResult, SolveStatus
)
from research.evaluation.metrics_evaluator import (
    MetricsEvaluator,
    TrackEvent, AllocationEvent, EngagementResult,
    evaluate_from_logs
)


def simulate_tracks():
    """Simulate track data that would come from AFSIM via shared memory."""
    return [
        Target(1001, 5.0, 300, "aircraft", 30.5, 119.5, 30000, {101: 80, 102: 120, 103: 150}),
        Target(1002, 5.0, 280, "aircraft", 30.8, 119.8, 28000, {101: 90, 102: 110, 103: 140}),
        Target(2001, 10.0, 500, "missile", 31.0, 120.0, 5000, {101: 100, 102: 150, 103: 180}),
        Target(3001, 8.0, 200, "ucav", 30.3, 119.2, 15000, {101: 70, 102: 100, 103: 130}),
    ]


def simulate_sensors():
    return [
        Sensor(101, 150, "track", 60, 30),
        Sensor(102, 120, "search", 90, 45),
        Sensor(103, 200, "track", 45, 20),
    ]


def simulate_weapons():
    return [
        Weapon(201, 100, 0.80, 1200, "aa_missile"),
        Weapon(202, 80, 0.75, 1000, "sam"),
        Weapon(203, 60, 0.90, 800, "aa_missile"),
        Weapon(204, 40, 0.70, 1500, "short_range"),
    ]


def run_milp_allocation(tracks, sensors, weapons):
    """Run MILP allocation."""
    print("\n" + "="*60)
    print("1. MILP ALLOCATION (OR-Tools / Greedy Fallback)")
    print("="*60)
    
    allocator = MilpAllocator(time_limit_sec=10, verbose=False)
    result = allocator.solve(tracks, sensors, weapons)
    
    print(f"   Status: {result.status.value}")
    print(f"   Solve time: {result.solve_time_sec:.2f}s")
    print(f"   Total score: {result.total_priority_score:.2f}")
    print(f"   Allocations: {len(result.allocations)}")
    
    for alloc in result.allocations:
        print(f"   Target {alloc.target_id} -> Sensor {alloc.sensor_id} + Weapon {alloc.weapon_id}")
        print(f"      Score: {alloc.priority_score:.3f}, Intercept: {alloc.intercept_time_sec:.1f}s")
    
    if result.unassigned_targets:
        print(f"   Unassigned: {result.unassigned_targets}")
    
    return result


def run_munkres_like_allocation(tracks, n_weapons):
    """Simple Munkres-style allocation (for demonstration)."""
    print("\n" + "="*60)
    print("2. HUNGARIAN-STYLE ALLOCATION")
    print("="*60)
    
    # Build cost matrix
    n = len(tracks)
    cost_matrix = []
    for t in tracks:
        row = []
        for w_idx in range(n_weapons):
            # Cost based on priority and range
            base_cost = 10 + w_idx * 3
            if t.type == "missile":
                mult = 0.5  # Missiles get priority (lower cost)
            elif t.type == "ucav":
                mult = 0.7
            else:
                mult = 1.0
            row.append(base_cost * mult)
        cost_matrix.append(row)
    
    # Simple greedy-by-cost allocation
    assignments = []
    for i, row in enumerate(cost_matrix):
        min_j = min(range(len(row)), key=lambda j: row[j])
        assignments.append((i, min_j))
        print(f"   Target {tracks[i].id} -> Weapon {201 + min_j} (cost={row[min_j]:.1f})")
    
    return assignments


def run_greedy_allocation(tracks, sensors, weapons):
    """Greedy allocation by priority score."""
    print("\n" + "="*60)
    print("3. GREEDY PRIORITY ALLOCATION")
    print("="*60)
    
    # Sort by priority (highest first)
    sorted_tracks = sorted(tracks, key=lambda t: t.priority, reverse=True)
    
    sensor_used = {s.id: False for s in sensors}
    weapon_used = {w.id: False for w in weapons}
    
    allocations = []
    for t in sorted_tracks:
        best_score = -1
        best_alloc = None
        
        for s in sensors:
            if sensor_used[s.id]:
                continue
            if s.id not in t.range_to_sensors:
                continue
            if t.range_to_sensors[s.id] > s.range_km:
                continue
            
            for w in weapons:
                if weapon_used[w.id]:
                    continue
                if t.velocity_kts > w.max_target_speed_kts:
                    continue
                if w.range_km < 20:
                    continue
                
                # Score = priority * kill_prob * coverage
                coverage = 1.0 - (t.range_to_sensors[s.id] / s.range_km) * 0.5
                score = (t.priority / 10.0) * w.kill_probability * coverage
                
                if score > best_score:
                    best_score = score
                    best_alloc = Allocation(
                        target_id=t.id,
                        sensor_id=s.id,
                        weapon_id=w.id,
                        priority_score=score,
                        intercept_time_sec=20.0,
                        kill_probability=w.kill_probability
                    )
        
        if best_alloc:
            allocations.append(best_alloc)
            sensor_used[best_alloc.sensor_id] = True
            weapon_used[best_alloc.weapon_id] = True
            print(f"   Target {t.id} -> Sensor {best_alloc.sensor_id} + Weapon {best_alloc.weapon_id}")
            print(f"      Priority: {t.priority}, Score: {best_score:.3f}")
    
    return allocations


def run_metrics_evaluation(allocations):
    """Run metrics evaluation."""
    print("\n" + "="*60)
    print("4. METRICS EVALUATION")
    print("="*60)
    
    now = time.time()
    
    # Build track events
    track_events = []
    for i, alloc in enumerate(allocations):
        track_events.append(TrackEvent(
            track_id=alloc.target_id,
            event_type="created",
            timestamp=now - 100 + i * 10,
            lat=30.5 + i * 0.1,
            lon=119.5 + i * 0.1,
            alt=10000 + i * 1000
        ))
        track_events.append(TrackEvent(
            track_id=alloc.target_id,
            event_type="killed",
            timestamp=now - 50 + i * 5,
            lat=31.0 + i * 0.1,
            lon=120.0 + i * 0.1,
            alt=12000 + i * 1000
        ))
    
    # Build allocation events
    alloc_events = []
    for alloc in allocations:
        alloc_events.append(AllocationEvent(
            target_id=alloc.target_id,
            sensor_id=alloc.sensor_id,
            weapon_id=alloc.weapon_id,
            decision_time_sec=3.5,
            priority_score=alloc.priority_score,
            intercept_time_sec=alloc.intercept_time_sec,
            timestamp=now - 90
        ))
    
    # Build engagement events (simulate outcomes)
    engagement_results = []
    for alloc in allocations:
        # Higher priority targets more likely to be killed
        outcome = "killed" if alloc.priority_score > 0.5 else "neutralized"
        engagement_results.append(EngagementResult(
            target_id=alloc.target_id,
            weapon_id=alloc.weapon_id,
            intercept_time_sec=alloc.intercept_time_sec,
            p_kill_actual=alloc.kill_probability,
            outcome=outcome,
            timestamp=now - 30
        ))
    
    # Evaluate
    evaluator = MetricsEvaluator()
    summary = evaluator.evaluate(track_events, alloc_events, engagement_results)
    
    print(evaluator.print_summary(summary))
    
    return summary


def main():
    """Run the complete kill chain integration test."""
    print("\n" + "#"*60)
    print("# KILL CHAIN MANAGEMENT - INTEGRATION TEST")
    print("# Full End-to-End Flow Demonstration")
    print("#"*60)
    
    start_time = time.time()
    
    # Step 0: Simulate AFSIM data
    print("\n[STEP 0] Generating simulated track data...")
    tracks = simulate_tracks()
    sensors = simulate_sensors()
    weapons = simulate_weapons()
    print(f"   Generated {len(tracks)} tracks, {len(sensors)} sensors, {len(weapons)} weapons")
    
    # Step 1: MILP Allocation
    milp_result = run_milp_allocation(tracks, sensors, weapons)
    
    # Step 2: Hungarian-style allocation
    hungarian_assignments = run_munkres_like_allocation(tracks, len(weapons))
    
    # Step 3: Greedy allocation
    greedy_allocs = run_greedy_allocation(tracks, sensors, weapons)
    
    # Step 4: Metrics Evaluation (using greedy results)
    metrics = run_metrics_evaluation(greedy_allocs)
    
    # Summary
    total_time = time.time() - start_time
    
    print("\n" + "#"*60)
    print("# INTEGRATION TEST COMPLETE")
    print("#"*60)
    print(f"   Total execution time: {total_time:.2f}s")
    print(f"   Tracks processed: {len(tracks)}")
    print(f"   MILP allocations: {len(milp_result.allocations)}")
    print(f"   Greedy allocations: {len(greedy_allocs)}")
    print(f"   Composite metrics score: {metrics.composite_score:.1f}/100")
    
    # Determine pass/fail
    if metrics.composite_score >= 40 and len(greedy_allocs) >= 2:
        status = "PASS"
    elif metrics.composite_score >= 25:
        status = "ACCEPTABLE"
    else:
        status = "NEEDS IMPROVEMENT"
    
    print(f"   Status: {status}")
    print("#"*60 + "\n")
    
    return metrics.composite_score >= 25


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
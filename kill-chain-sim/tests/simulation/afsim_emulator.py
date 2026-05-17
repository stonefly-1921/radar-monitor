"""
AFSIM Simulation Emulator - Generates realistic track data for testing

Simulates what AFSIM would produce via shared memory:
- Track creation events
- Track updates (position, velocity)
- Engagement outcomes
- Kill chain events

Run: python -m tests.simulation.afsim_emulator
"""

import sys
import os
import time
import random
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from research.evaluation.metrics_evaluator import (
    MetricsEvaluator,
    TrackEvent, AllocationEvent, EngagementResult
)


# Simulation parameters
SIM_DURATION_SEC = 120  # 2 minute simulation
UPDATE_INTERVAL_SEC = 1.0  # Track update every 1 second
TRACK_CREATION_INTERVAL = 15  # New track every 15 seconds
NUM_INITIAL_TARGETS = 3


class SimulatedTarget:
    """Represents a simulated target in the battlespace."""
    
    def __init__(self, track_id, lat, lon, alt, speed, heading, target_type):
        self.track_id = track_id
        self.lat = lat
        self.lon = lon
        self.alt = alt
        self.speed = speed  # kts
        self.heading = heading  # degrees
        self.target_type = target_type
        self.alive = True
        self.killed_time = None
        self.creation_time = time.time()
        
        # Movement
        self._lat_rate = speed * math.cos(math.radians(heading)) / 60000  # deg/sec
        self._lon_rate = speed * math.sin(math.radians(heading)) / 60000
        
    def update(self, dt):
        """Update position based on movement."""
        if not self.alive:
            return
        self.lat += self._lat_rate * dt
        self.lon += self._lon_rate * dt
    
    def kill(self):
        self.alive = False
        self.killed_time = time.time()


class AFSIMEmulator:
    """
    Emulates AFSIM simulation output for kill chain testing.
    
    Produces:
    - Track events (created, updated, lost, killed)
    - Allocation decisions (from kill chain manager)
    - Engagement outcomes
    """
    
    def __init__(self, seed=42):
        random.seed(seed)
        self.targets = {}
        self.track_events = []
        self.allocations = []
        self.engagements = []
        self.next_track_id = 1000
        self.sensor_assignment = {}  # track_id -> sensor_id
        self.weapon_assignment = {}  # track_id -> weapon_id
        
    def create_target(self, target_type="aircraft"):
        """Create a new target."""
        tid = self.next_track_id
        self.next_track_id += 1
        
        # Random position within battlespace
        lat = random.uniform(30.0, 32.0)
        lon = random.uniform(118.0, 121.0)
        alt = random.choice([5000, 10000, 20000, 30000])  # ft
        
        if target_type == "missile":
            speed = random.uniform(400, 600)  # Fast
            alt = random.choice([1000, 3000, 5000])  # Low
        elif target_type == "ucav":
            speed = random.uniform(150, 250)
            alt = random.choice([5000, 10000, 15000])
        else:
            speed = random.uniform(250, 400)
        
        heading = random.uniform(0, 360)
        
        target = SimulatedTarget(tid, lat, lon, alt, speed, heading, target_type)
        self.targets[tid] = target
        
        return target
    
    def generate_initial_targets(self, count=3):
        """Generate initial set of targets."""
        types = ["aircraft", "aircraft", "missile", "ucav"]
        for i in range(count):
            t = self.create_target(types[i % len(types)])
    
    def process_allocations(self, current_time):
        """
        Simulate allocation decisions from kill chain manager.
        For each alive target, decide if we allocate to it.
        """
        for tid, target in self.targets.items():
            if not target.alive:
                continue
            
            # Simulate kill chain manager decision
            # Higher priority targets (missiles) get allocated faster
            if target.target_type == "missile":
                alloc_delay = random.uniform(1.0, 3.0)
            elif target.target_type == "ucav":
                alloc_delay = random.uniform(2.0, 5.0)
            else:
                alloc_delay = random.uniform(3.0, 8.0)
            
            # Only allocate if target alive long enough
            age = current_time - target.creation_time
            if age >= alloc_delay and tid not in self.weapon_assignment:
                # Allocate sensor and weapon
                sensor_id = random.choice([101, 102, 103])
                weapon_id = random.choice([201, 202, 203, 204])
                
                self.sensor_assignment[tid] = sensor_id
                self.weapon_assignment[tid] = weapon_id
                
                # Record allocation event
                self.allocations.append(AllocationEvent(
                    target_id=tid,
                    sensor_id=sensor_id,
                    weapon_id=weapon_id,
                    decision_time_sec=alloc_delay,
                    priority_score=random.uniform(0.6, 0.95),
                    intercept_time_sec=random.uniform(10, 30),
                    timestamp=current_time
                ))
    
    def process_engagements(self, current_time):
        """Simulate engagement outcomes for allocated targets."""
        for tid, weapon_id in list(self.weapon_assignment.items()):
            if tid not in self.targets:
                continue
            
            target = self.targets[tid]
            if not target.alive:
                continue
            
            # Check if engagement happens
            if random.random() < 0.7:  # 70% chance of engagement
                # Determine outcome
                rand = random.random()
                if rand < 0.6:  # 60% killed
                    outcome = "killed"
                    target.kill()
                elif rand < 0.85:  # 25% neutralized
                    outcome = "neutralized"
                    target.kill()
                elif rand < 0.95:  # 10% escaped
                    outcome = "escaped"
                else:  # 5% failed
                    outcome = "failed"
                
                self.engagements.append(EngagementResult(
                    target_id=tid,
                    weapon_id=weapon_id,
                    intercept_time_sec=random.uniform(8, 25),
                    p_kill_actual=random.uniform(0.6, 0.9),
                    outcome=outcome,
                    timestamp=current_time
                ))
    
    def run_simulation(self, duration=120):
        """Run the full simulation."""
        print("=" * 60)
        print("AFSIM EMULATION - Kill Chain Simulation")
        print("=" * 60)
        
        start_time = time.time()
        end_time = start_time + duration
        sim_time = start_time
        
        # Generate initial targets
        self.generate_initial_targets(NUM_INITIAL_TARGETS)
        
        # Create initial track events
        for tid, target in self.targets.items():
            self.track_events.append(TrackEvent(
                track_id=tid,
                event_type="created",
                timestamp=start_time,
                lat=target.lat,
                lon=target.lon,
                alt=target.alt
            ))
        
        print(f"\n[SIM] Started at t=0")
        print(f"[SIM] Initial targets: {len(self.targets)}")
        
        step = 0
        while sim_time < end_time:
            dt = UPDATE_INTERVAL_SEC
            sim_time += dt
            
            # Spawn new targets periodically
            if step % TRACK_CREATION_INTERVAL == 0 and len(self.targets) < 8:
                new_type = random.choice(["aircraft", "missile", "ucav"])
                target = self.create_target(new_type)
                self.track_events.append(TrackEvent(
                    track_id=target.track_id,
                    event_type="created",
                    timestamp=sim_time,
                    lat=target.lat,
                    lon=target.lon,
                    alt=target.alt
                ))
                print(f"[SIM] t={sim_time-start_time:.0f}s: New target {target.track_id} ({target.target_type})")
            
            # Update targets
            for target in self.targets.values():
                if target.alive:
                    target.update(dt)
                    # Record update (throttled)
                    if step % 10 == 0:
                        self.track_events.append(TrackEvent(
                            track_id=target.track_id,
                            event_type="updated",
                            timestamp=sim_time,
                            lat=target.lat,
                            lon=target.lon,
                            alt=target.alt
                        ))
            
            # Process allocations
            self.process_allocations(sim_time)
            
            # Process engagements
            self.process_engagements(sim_time)
            
            step += 1
        
        # Check for any remaining alive targets (mark as escaped/lost)
        current_time = sim_time
        for tid, target in self.targets.items():
            if target.alive:
                self.track_events.append(TrackEvent(
                    track_id=tid,
                    event_type="lost",
                    timestamp=current_time,
                    lat=target.lat,
                    lon=target.lon,
                    alt=target.alt
                ))
        
        print(f"\n[SIM] Simulation complete at t={duration}s")
        print(f"[SIM] Total track events: {len(self.track_events)}")
        print(f"[SIM] Total allocations: {len(self.allocations)}")
        print(f"[SIM] Total engagements: {len(self.engagements)}")
        
        return self.track_events, self.allocations, self.engagements


def evaluate_simulation(track_events, allocations, engagements):
    """Evaluate the simulation with metrics."""
    print("\n" + "=" * 60)
    print("METRICS EVALUATION")
    print("=" * 60)
    
    evaluator = MetricsEvaluator()
    summary = evaluator.evaluate(track_events, allocations, engagements)
    
    print(evaluator.print_summary(summary))
    
    return summary


def main():
    """Run AFSIM emulation and evaluate."""
    print("\n" + "#" * 60)
    print("# AFSIM EMULATION MODE")
    print("# Simulating 120 seconds of kill chain operations")
    print("#" * 60)
    
    # Create emulator and run
    emulator = AFSIMEmulator(seed=12345)
    tracks, allocs, engagements = emulator.run_simulation(duration=SIM_DURATION_SEC)
    
    # Evaluate
    summary = evaluate_simulation(tracks, allocs, engagements)
    
    # Print final summary
    print("\n" + "#" * 60)
    print("# AFSIM EMULATION RESULTS")
    print("#" * 60)
    print(f"Simulation Duration: {SIM_DURATION_SEC}s")
    print(f"Targets Created: {len([t for t in tracks if t.event_type == 'created'])}")
    print(f"Allocations Processed: {len(allocs)}")
    print(f"Engagements: {len(engagements)}")
    print()
    print("KILL CHAIN PERFORMANCE:")
    print(f"  Track Continuity:      {summary.track_continuity_score:.1f}/100")
    print(f"  Allocation Efficiency: {summary.allocation_efficiency_score:.1f}/100")
    print(f"  Engagement Effect.:    {summary.engagement_effectiveness_score:.1f}/100")
    print(f"  OODA Loop Speed:       {summary.ooda_loop_score:.1f}/100")
    print(f"  Coverage:              {summary.coverage_score:.1f}/100")
    print()
    print(f"  COMPOSITE SCORE:       {summary.composite_score:.1f}/100")
    
    # Engagement breakdown
    killed = sum(1 for e in engagements if e.outcome == "killed")
    neutralized = sum(1 for e in engagements if e.outcome == "neutralized")
    escaped = sum(1 for e in engagements if e.outcome == "escaped")
    failed = sum(1 for e in engagements if e.outcome == "failed")
    
    print(f"\nENGAGEMENT BREAKDOWN:")
    print(f"  Killed:       {killed}")
    print(f"  Neutralized:  {neutralized}")
    print(f"  Escaped:      {escaped}")
    print(f"  Failed:       {failed}")
    
    total_eng = len(engagements)
    if total_eng > 0:
        kill_rate = (killed + neutralized) / total_eng * 100
        print(f"  Effectiveness: {kill_rate:.1f}%")
    
    print("#" * 60)
    
    return summary


if __name__ == "__main__":
    summary = main()
    
    # Exit code based on score
    if summary.composite_score >= 60:
        sys.exit(0)
    else:
        sys.exit(1)
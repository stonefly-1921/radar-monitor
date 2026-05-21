#!/usr/bin/env python3
"""
kill_chain_1v1_demo.py - Parse 1v1 AFSIM LOG.1, run MILP + Metrics

Usage:
    python kill_chain_1v1_demo.py
"""

import os
import sys
import re
import json
import math
from datetime import datetime

PROJECT_ROOT = r"C:\Users\15041\.openclaw\workspace\kill-chain-sim"
sys.path.insert(0, PROJECT_ROOT)

from src.research.algorithms.milp_allocator import (
    MilpAllocator, Target, Sensor, Weapon, SolveStatus
)
from src.research.evaluation.metrics_evaluator import (
    MetricsEvaluator, TrackEvent, AllocationEvent, EngagementResult
)


# ============================================================================
# Config
# ============================================================================
AFSIM_LOG = r"D:\afsim-2.9.0-win64\demos\air_to_air\output\LOG.1"
OUTPUT_DIR = r"D:\afsim-2.9.0-win64\output"

# Sensor/Weapon config (蓝方资源)
SENSORS = [
    {"id": 1, "range_km": 300, "mode": "track", "azimuth_fov": 120, "elevation_fov": 60},
    {"id": 2, "range_km": 200, "mode": "search", "azimuth_fov": 360, "elevation_fov": 90},
]
WEAPONS = [
    {"id": 1, "range_km": 150, "kill_prob": 0.85, "max_speed": 1500, "type": "aa_missile"},
    {"id": 2, "range_km": 80,  "kill_prob": 0.70, "max_speed": 1200, "type": "sam"},
    {"id": 3, "range_km": 100, "kill_prob": 0.75, "max_speed": 1000, "type": "sam"},
]


# ============================================================================
# Kill Chain State
# ============================================================================
class KillChainState:
    def __init__(self):
        self.platforms = {}     # id -> {name, side, type, killed_time, killed}
        self.weapon_firings = []  # [(time, weapon_name, shooter_id, target_id, killed)]
        self.engagements = []     # EngagementResult
        self.alloc_events = []    # AllocationEvent
        self.milp_allocations = []
        self.sim_duration = 0.0

state = KillChainState()


# ============================================================================
# Parse LOG.1
# ============================================================================
def parse_log(log_path):
    """Parse AFSIM LOG.1 file and extract kill chain events."""
    events = []
    
    # Regex patterns
    platform_pat = re.compile(r"^A/C\s+(\d+)\s+(\w+)\s+(\S+)\s+\(([^)]+)\)")
    missile_fired_pat = re.compile(r"^ MISSILE (\S+) \(([^)]+)\) FIRED AT (\d+)\s+BY\s+(\d+)\s+AT TIME ([\d.]+)")
    mslend_pat = re.compile(r"^ MSLEND\.\.MISSILE (\S+)\(([^)]+)\s+\) VS TGT\s+(\d+)\s+KILL=\s+(\w)")
    killed_pat = re.compile(r"^ A/C\s+(\d+)\s+IS KILLED AT TIME\s+([\d.]+)")
    time_marker_pat = re.compile(r"^\*\* SIMULATION TIME HAS REACHED\s+([\d.]+)")
    
    with open(log_path, 'r', errors='replace') as f:
        for line in f:
            line = line.rstrip()
            
            # Platform state
            m = platform_pat.match(line)
            if m:
                plat_id, side, name, pos_info = m.groups()
                events.append({"type": "platform", "time": None,
                               "id": int(plat_id), "side": side, "name": name})
                continue
                
            # Missile fired
            m = missile_fired_pat.match(line)
            if m:
                weapon_name, weapon_type, target_id, shooter_id, t = m.groups()
                events.append({"type": "fired", "time": float(t),
                               "weapon": weapon_name, "weapon_type": weapon_type,
                               "shooter_id": int(shooter_id), "target_id": int(target_id)})
                continue
                
            # Missile end (kill/miss)
            m = mslend_pat.match(line)
            if m:
                weapon_name, weapon_type, target_id, kill_flag = m.groups()
                events.append({"type": "mslend", "time": None,
                               "weapon": weapon_name, "target_id": int(target_id),
                               "kill": kill_flag == "T"})
                continue
                
            # Platform killed
            m = killed_pat.match(line)
            if m:
                plat_id, t = m.groups()
                events.append({"type": "killed", "time": float(t), "id": int(plat_id)})
                continue
                
            # Sim time marker
            m = time_marker_pat.match(line)
            if m:
                events.append({"type": "time_marker", "time": float(m.group(1))})
                continue
    
    return events


def process_events(events):
    """Convert parsed events to kill chain state."""
    firings = []  # track fired events to match with kills
    
    for evt in events:
        if evt["type"] == "fired":
            state.weapon_firings.append({
                "time": evt["time"],
                "weapon": evt["weapon"],
                "weapon_type": evt["weapon_type"],
                "shooter_id": evt["shooter_id"],
                "target_id": evt["target_id"],
                "result": "unknown"
            })
            
        elif evt["type"] == "mslend":
            # Match to most recent firing of same weapon
            for f in reversed(state.weapon_firings):
                if f["weapon"] == evt["weapon"] and f["result"] == "unknown":
                    f["result"] = "KILL" if evt["kill"] else "MISS"
                    break
                    
        elif evt["type"] == "killed":
            state.platforms[evt["id"]]["killed_time"] = evt["time"]
            state.platforms[evt["id"]]["killed"] = True
            
            # Find the firing that killed this platform
            for f in reversed(state.weapon_firings):
                if f["target_id"] == evt["id"] and f["result"] in ("KILL", "MISS"):
                    state.engagements.append(EngagementResult(
                        target_id=evt["id"],
                        weapon_id=1,
                        p_kill_actual=1.0 if f["result"] == "KILL" else 0.0,
                        outcome="killed" if f["result"] == "KILL" else "escaped",
                        intercept_time_sec=f["time"],
                        timestamp=evt["time"]
                    ))
                    break
                
        elif evt["type"] == "platform" and evt["id"] not in state.platforms:
            state.platforms[evt["id"]] = {
                "name": evt["name"],
                "side": evt["side"],
                "killed": False,
                "killed_time": None
            }
            
        elif evt["type"] == "time_marker":
            state.sim_duration = max(state.sim_duration, evt["time"])
    
    # Build track events from platform data
    track_events = []
    for plat_id, plat in state.platforms.items():
        side_num = {"blue": 2, "red": 1, "neutral": 0}.get(plat["side"], 0)
        track_events.append(TrackEvent(
            track_id=plat_id,
            event_type="created",
            timestamp=0,
            lat=0, lon=0, alt=0
        ))
        if plat["killed"] and plat["killed_time"]:
            track_events.append(TrackEvent(
                track_id=plat_id,
                event_type="killed",
                timestamp=plat["killed_time"],
                lat=0, lon=0, alt=0
            ))
    
    return track_events


# ============================================================================
# MILP Allocation
# ============================================================================
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def run_milp(tracks):
    """Run MILP on tracks."""
    targets = []
    radar_lat, radar_lon = 38.0683, -117.2333
    
    for t in tracks:
        range_to_sensors = {}
        for s in SENSORS:
            # Simulate target positions (in real system, use actual track location)
            dist_km = haversine_km(t["lat"], t["lon"], radar_lat, radar_lon) if t["lat"] else 200
            range_to_sensors[s["id"]] = dist_km
        
        side_num = t.get("side_num", 0)
        if side_num == 2:  # blue
            priority = 5.0
        elif side_num == 1:  # red
            priority = 10.0
        else:
            priority = 5.0
        
        targets.append(Target(
            id=t["track_id"],
            priority=priority,
            velocity_kts=500,
            type="aircraft",
            lat=t.get("lat", 0),
            lon=t.get("lon", 0),
            altitude_ft=30000,
            range_to_sensors=range_to_sensors
        ))
    
    milp_sensors = [Sensor(
        id=s["id"], range_km=s["range_km"], mode=s["mode"],
        azimuth_fov_deg=s["azimuth_fov"], elevation_fov_deg=s["elevation_fov"]
    ) for s in SENSORS]
    
    milp_weapons = [Weapon(
        id=w["id"], range_km=w["range_km"],
        kill_probability=w["kill_prob"],
        max_target_speed_kts=w["max_speed"],
        type=w["type"]
    ) for w in WEAPONS]
    
    allocator = MilpAllocator(time_limit_sec=5, verbose=False)
    result = allocator.solve(targets, milp_sensors, milp_weapons)
    
    return result


# ============================================================================
# Main
# ============================================================================
def main():
    print("=" * 60)
    print("Kill Chain 1v1 Demo - AFSIM LOG.1 Parser + MILP + Metrics")
    print("=" * 60)
    
    # Parse LOG.1
    print(f"\nParsing: {AFSIM_LOG}")
    events = parse_log(AFSIM_LOG)
    
    # Categorize
    platforms = [e for e in events if e["type"] == "platform"]
    firings = [e for e in events if e["type"] == "fired"]
    kills = [e for e in events if e["type"] == "killed"]
    mslends = [e for e in events if e["type"] == "mslend"]
    
    print(f"\nParsed {len(events)} events:")
    print(f"  Platform states: {len(platforms)}")
    print(f"  Weapon firings:  {len(firings)}")
    print(f"  Weapon results:  {len(mslends)}")
    print(f"  Platform kills:  {len(kills)}")
    
    # Process into state
    track_events = process_events(events)
    
    print(f"\nKill Chain State:")
    print(f"  Platforms tracked: {len(state.platforms)}")
    for pid, plat in state.platforms.items():
        status = f"KILLED at t={plat['killed_time']:.0f}s" if plat["killed"] else "ALIVE"
        print(f"    id={pid} {plat['name']} ({plat['side']}) - {status}")
    
    print(f"\nWeapon Firings:")
    for f in state.weapon_firings:
        print(f"    t={f['time']:.0f}s {f['weapon']} shooter={f['shooter_id']} -> target={f['target_id']} result={f['result']}")
    
    print(f"\nEngagements recorded: {len(state.engagements)}")
    
    # Build tracks for MILP (from platform data)
    tracks = []
    for pid, plat in state.platforms.items():
        side_map = {"blue": 2, "red": 1, "neutral": 0}
        tracks.append({
            "track_id": pid,
            "lat": 38.0 + pid * 0.1,  # simulated positions
            "lon": -117.2 - pid * 0.1,
            "alt": 9144,  # 30000 ft
            "side_num": side_map.get(plat["side"], 0)
        })
    
    # Run MILP
    print(f"\nRunning MILP allocation on {len(tracks)} targets...")
    result = run_milp(tracks)
    print(f"MILP result: status={result.status.value}")
    print(f"  Score: {result.total_priority_score:.2f}")
    print(f"  Allocations: {len(result.allocations)}")
    print(f"  Unassigned: {result.unassigned_targets}")
    
    for alloc in result.allocations:
        wtype = WEAPONS[alloc.weapon_id - 1]["type"] if alloc.weapon_id <= len(WEAPONS) else "?"
        print(f"    target={alloc.target_id} sensor={alloc.sensor_id} weapon={alloc.weapon_id} ({wtype}) "
              f"score={alloc.priority_score:.2f} P_kill={alloc.kill_probability:.0%}")
        
        # Record allocation
        state.alloc_events.append(AllocationEvent(
            target_id=alloc.target_id,
            sensor_id=alloc.sensor_id,
            weapon_id=alloc.weapon_id,
            decision_time_sec=10.0,  # simulated
            priority_score=alloc.priority_score / 10.0,
            intercept_time_sec=alloc.intercept_time_sec,
            timestamp=10.0
        ))
        state.milp_allocations.append(alloc)
    
    # Evaluate
    print(f"\n" + "=" * 60)
    print("METRICS EVALUATION")
    print("=" * 60)
    
    evaluator = MetricsEvaluator()
    
    # Build coverage grid (simplified)
    coverage_grid = {}
    radar_lat, radar_lon = 38.0683, -117.2333
    for lat_i in range(-5, 6):
        for lon_i in range(-5, 6):
            dist = haversine_km(radar_lat + lat_i*0.01, radar_lon + lon_i*0.01,
                              radar_lat, radar_lon)
            coverage_grid[(lat_i+5, lon_i+5)] = max(0, 1 - dist/300)
    
    summary = evaluator.evaluate(
        track_events=track_events,
        allocations=state.alloc_events,
        engagements=state.engagements,
        coverage_grid=coverage_grid if coverage_grid else None
    )
    
    evaluator.print_summary(summary)
    
    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "source": "1v1 AFSIM Demo LOG.1",
        "sim_duration_sec": state.sim_duration,
        "total_platforms": len(state.platforms),
        "weapon_firings": len(state.weapon_firings),
        "kills": len([f for f in state.weapon_firings if f["result"] == "KILL"]),
        "misses": len([f for f in state.weapon_firings if f["result"] == "MISS"]),
        "milp_allocations": len(state.alloc_events),
        "metrics": summary.to_dict() if hasattr(summary, 'to_dict') else dict(summary._asdict()) if hasattr(summary, '_asdict') else {},
        "per_firing": [
            {"time": f["time"], "weapon": f["weapon"], "shooter": f["shooter_id"],
             "target": f["target_id"], "result": f["result"]}
            for f in state.weapon_firings
        ]
    }
    
    report_path = os.path.join(OUTPUT_DIR, "kill_chain_1v1_metrics.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved: {report_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
kill_chain_sim.py - AFSIM Kill Chain Simulation with MILP Allocation & Metrics

Pipeline:
  AFSIM stdout (writeln TRACK:) → Python track parser
    → MilpAllocator.solve() → Allocation decisions
    → MetricsEvaluator.evaluate() → Performance scores

Usage:
    python kill_chain_sim.py
"""

import os
import sys
import time
import json
import threading
import subprocess
import win32pipe
import win32file
from datetime import datetime

# Add project root to path for imports
PROJECT_ROOT = r"C:\Users\15041\.openclaw\workspace\kill-chain-sim"
sys.path.insert(0, PROJECT_ROOT)

from src.research.algorithms.milp_allocator import (
    MilpAllocator, Target, Sensor, Weapon,
    SolveStatus
)
from src.research.evaluation.metrics_evaluator import (
    MetricsEvaluator, TrackEvent, AllocationEvent, EngagementResult
)


# ============================================================================
# Configuration
# ============================================================================
AFSIM_ROOT = r"D:\afsim-2.9.0-win64"
AFSIM_BIN = os.path.join(AFSIM_ROOT, "bin", "mission.exe")
SCENARIO_FILE = os.path.join(PROJECT_ROOT, "src", "sim", "kill_chain_np.txt")
PIPE_NAME = r"\\.\pipe\KILL_CHAIN_CMD"
LOG_FILE = os.path.join(AFSIM_ROOT, "output", "kill_chain_sim.log")

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
        self.tracks = {}        # track_id -> {lat, lon, alt, side, speed, heading, ...}
        self.track_events = []   # [TrackEvent, ...]
        self.alloc_events = []  # [AllocationEvent, ...]  (for metrics)
        self.milp_allocations = []  # raw allocations from MILP
        self.engagements = []   # [EngagementResult, ...]
        self.cmd_history = []
        self.start_time = None  # wall clock when sim started
        self.sim_start_time = 0.0  # AFSIM sim time when first track seen
        self.running = True
        self.lock = threading.Lock()
        self._track_first_seen = {}  # track_id -> sim_time (AFSIM seconds)
        self._allocated_keys = set()  # (target_id, sensor_id, weapon_id) dedup across all cycles

    def update_track(self, track_id, lat, lon, alt, side="neutral", speed=0, heading=0, sim_time=0.0):
        with self.lock:
            is_new = track_id not in self.tracks
            if is_new:
                if not self._track_first_seen:
                    self.sim_start_time = sim_time
                self.track_events.append(TrackEvent(
                    track_id=track_id, event_type="created",
                    timestamp=sim_time, lat=lat, lon=lon, alt=alt
                ))
                self._track_first_seen[track_id] = sim_time
            else:
                self.track_events.append(TrackEvent(
                    track_id=track_id, event_type="updated",
                    timestamp=sim_time, lat=lat, lon=lon, alt=alt
                ))
            self.tracks[track_id] = {
                "track_id": track_id, "lat": lat, "lon": lon, "alt": alt,
                "side": side, "speed": speed, "heading": heading,
                "last_update": sim_time,
            }

    def record_allocation(self, alloc, decision_time_sec, normalized_priority=0.5):
        with self.lock:
            self.alloc_events.append(AllocationEvent(
                target_id=alloc.target_id,
                sensor_id=alloc.sensor_id,
                weapon_id=alloc.weapon_id,
                decision_time_sec=decision_time_sec,
                priority_score=normalized_priority,
                intercept_time_sec=alloc.intercept_time_sec,
                timestamp=time.time()
            ))

    def get_tracks(self):
        with self.lock:
            return list(self.tracks.values())

state = KillChainState()


# ============================================================================
# Logging
# ============================================================================
def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    entry = f"[{ts}] [{level}] {msg}"
    print(entry, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(entry + "\n")


# ============================================================================
# Parse TRACK lines from AFSIM stdout
# ============================================================================
_last_sim_time = 0.0
def parse_track_line(line):
    global _last_sim_time
    line = line.strip()
    if line.startswith("TRACK_COUNT:"):
        parts = line.split()
        result = {"type": "track_count", "tracks": 0, "time": 0}
        for p in parts:
            if p.startswith("tracks="): result["tracks"] = int(p.split("=")[1])
            elif p.startswith("time="):
                result["time"] = float(p.split("=")[1])
                _last_sim_time = result["time"]
        return result
    elif line.startswith("TRACK:") or line.startswith("WEAPON_HIT:") or line.startswith("WEAPON_MISS:"):
        # Handle both TRACK: and weapon result lines
        if line.startswith("WEAPON_"):
            try:
                # WEAPON_HIT: target_id=2 weapon=AIM-120 time=25.5
                # WEAPON_MISS: target_id=3 weapon=AIM-120 time=30.2
                parts = line.split()
                result = {"type": "weapon_result", "hit": "WEAPON_HIT" in line, "time": 0}
                for p in parts:
                    if p.startswith("target_id="): result["target_id"] = int(p.split("=")[1])
                    elif p.startswith("time="): result["time"] = float(p.split("=")[1])
                    elif p.startswith("weapon="): result["weapon"] = p.split("=")[1]
                if result.get("target_id"):
                    _last_sim_time = result.get("time", _last_sim_time)
                    return result
            except:
                return None
        # TRACK: line
        try:
            data = line[6:].split(",")
            side_num = int(data[4]) if data[4] else 0
            side_map = {0: "neutral", 1: "red", 2: "blue", 3: "friendly"}
            side = side_map.get(side_num, f"side{side_num}")
            return {
                "type": "track",
                "track_id": data[0],
                "lat": float(data[1]), "lon": float(data[2]), "alt": float(data[3]),
                "side": side, "side_num": side_num,
                "speed": float(data[5]) if len(data) > 5 and data[5] else 0,
                "heading": float(data[6]) if len(data) > 6 and data[6] else 0,
                "sim_time": _last_sim_time  # from last TRACK_COUNT line
            }
        except:
            return None
    elif line.startswith("T = "):
        try:
            return {"type": "time_marker", "time": float(line.split("T = ")[1].strip())}
        except:
            return None
    return None


# ============================================================================
# MILP Kill Chain Allocator
# ============================================================================
def run_milp_allocation(tracks):
    """Convert tracks to MILP input, run optimizer, return allocations."""
    if not tracks:
        return []

    # Convert to MILP targets
    targets = []
    for t in tracks:
        # Estimate range to each sensor (simplified: use lat/lon distance)
        # In real system this would use actual sensor position + geometry
        range_to_sensors = {}
        for s in SENSORS:
            # RADAR at (38:04:06n, 117:14:00w) = (38.0683, -117.2333)
            radar_lat, radar_lon = 38.0683, -117.2333
            dist_km = haversine_km(t["lat"], t["lon"], radar_lat, radar_lon)
            range_to_sensors[s["id"]] = dist_km

        # Priority based on altitude + side (missiles = higher priority)
        alt = t["alt"]
        side = t.get("side_num", 0)
        if side == 2:  # blue
            priority = 5.0
        elif side == 1:  # red
            # Missiles (alt > 10000m) get highest priority
            if alt > 10000:
                priority = 10.0
            elif alt > 5000:
                priority = 8.0
            else:
                priority = 7.0
        else:
            priority = 5.0

        # Type classification
        if alt > 15000:
            ttype = "missile"
            velocity_kts = t.get("speed", 0) * 1.944  # m/s to kts
        elif alt > 3000:
            ttype = "aircraft"
            velocity_kts = max(t.get("speed", 150), 150)
        else:
            ttype = "ucav"
            velocity_kts = max(t.get("speed", 100), 100)

        targets.append(Target(
            id=int(t["track_id"]),
            priority=priority,
            velocity_kts=velocity_kts,
            type=ttype,
            lat=t["lat"],
            lon=t["lon"],
            altitude_ft=alt * 3.281,  # m to ft
            range_to_sensors=range_to_sensors
        ))

    # Convert sensors
    milp_sensors = [Sensor(
        id=s["id"], range_km=s["range_km"], mode=s["mode"],
        azimuth_fov_deg=s["azimuth_fov"], elevation_fov_deg=s["elevation_fov"]
    ) for s in SENSORS]

    # Convert weapons
    milp_weapons = [Weapon(
        id=w["id"], range_km=w["range_km"],
        kill_probability=w["kill_prob"],
        max_target_speed_kts=w["max_speed"],
        type=w["type"]
    ) for w in WEAPONS]

    # Run MILP
    allocator = MilpAllocator(time_limit_sec=5, verbose=False)
    result = allocator.solve(targets, milp_sensors, milp_weapons)

    log(f"[MILP] status={result.status.value} score={result.total_priority_score:.2f} "
        f"allocations={len(result.allocations)} unassigned={result.unassigned_targets} "
        f"solve_time={result.solve_time_sec:.3f}s", "MILP")

    return result.allocations


def haversine_km(lat1, lon1, lat2, lon2):
    """Calculate great-circle distance in km."""
    import math
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


# ============================================================================
# Kill Chain Decision Loop (with MILP)
# ============================================================================
def kill_chain_loop():
    log("Kill chain decision loop (MILP) started")
    last_alloc_time = 0
    last_status_time = 0

    while state.running:
        time.sleep(2)

        # Run MILP allocation every 10 AFSIM sim seconds
        if _last_sim_time - last_alloc_time >= 10:
            last_alloc_time = _last_sim_time
            tracks = state.get_tracks()
            if not tracks:
                continue

            log(f"[KC] Running MILP on {len(tracks)} tracks at t={_last_sim_time:.0f}s", "KC")
            allocs = run_milp_allocation(tracks)

            # Deduplicate: only record new (target, sensor, weapon) allocations across all cycles
            seen = set()
            for alloc in allocs:
                key = (alloc.target_id, alloc.sensor_id, alloc.weapon_id)
                if key in seen or key in state._allocated_keys:
                    continue
                seen.add(key)
                state._allocated_keys.add(key)

                # Normalize priority_score to 0-1 range (MILP gives 3-10, evaluator expects 0-1)
                normalized_score = min(1.0, alloc.priority_score / 10.0)

                # decision_time in AFSIM sim seconds
                t_first = state._track_first_seen.get(alloc.target_id, 0)
                decision_time = _last_sim_time - t_first if t_first > 0 else 0

                state.record_allocation(alloc, decision_time, normalized_score)

                # Log the decision
                weapon_name = WEAPONS[alloc.weapon_id - 1]["type"] if alloc.weapon_id <= len(WEAPONS) else "unknown"
                log(f"[ALLOC] target={alloc.target_id} sensor={alloc.sensor_id} weapon={alloc.weapon_id} "
                    f"({weapon_name}) score={normalized_score:.2f} "
                    f"P_kill={alloc.kill_probability:.0%} t_intercept={alloc.intercept_time_sec:.0f}s "
                    f"decision_time={decision_time:.0f}s", "ALLOC")

        # Periodic status
        if _last_sim_time - last_status_time >= 15:
            last_status_time = _last_sim_time
            blue = [t for t in state.get_tracks() if t.get("side") == "blue"]
            red  = [t for t in state.get_tracks() if t.get("side") == "red"]
            log(f"[STATUS] t={_last_sim_time:.0f}s tracks={len(state.tracks)} "
                f"red={len(red)} blue={len(blue)} "
                f"alloc_decisions={len(state.alloc_events)}")


# ============================================================================
# Named Pipe Server
# ============================================================================
BUFFER_SIZE = 4096

def pipe_server():
    log(f"Pipe server listening on {PIPE_NAME}")
    while state.running:
        try:
            hPipe = win32pipe.CreateNamedPipe(
                PIPE_NAME,
                win32pipe.PIPE_ACCESS_DUPLEX,
                win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                win32pipe.PIPE_UNLIMITED_INSTANCES,
                BUFFER_SIZE, BUFFER_SIZE, 0, None
            )
            if hPipe == -1 or hPipe is None:
                time.sleep(1)
                continue
            try:
                win32pipe.ConnectNamedPipe(hPipe, None)
            except Exception as e:
                log(f"ConnectNamedPipe error: {e}", "ERROR")
                win32file.CloseHandle(hPipe)
                continue

            log(f"AFSIM DLL connected: {hPipe}")

            while state.running:
                try:
                    hr, data = win32file.ReadFile(hPipe, BUFFER_SIZE)
                    if data:
                        cmd = data.decode('utf-8').strip()
                        log(f"[PIPE] CMD: {cmd!r}", "PIPE")
                        response = process_afsim_command(cmd)
                        if response:
                            win32file.WriteFile(hPipe, response.encode('utf-8'))
                except Exception as e:
                    log(f"Pipe read error: {e}", "ERROR")
                    break
            win32file.CloseHandle(hPipe)
        except Exception as e:
            log(f"Pipe server error: {e}", "ERROR")
            time.sleep(1)

def process_afsim_command(cmd):
    if cmd == "PING": return "PONG"
    elif cmd == "GET_TIME": return str(int(time.time() * 1000))
    elif cmd == "STATUS":
        return json.dumps({
            "server_status": "running",
            "tracks_tracked": len(state.tracks),
            "alloc_decisions": len(state.alloc_events),
            "milp_allocations": len(state.milp_allocations)
        })
    elif cmd.startswith("TRACK_CMD:"):
        # AFSIM can send commands via pipe
        return json.dumps({"ack": True, "cmd": cmd})
    else:
        return json.dumps({"error": f"Unknown: {cmd}"})


# ============================================================================
# AFSIM stdout Reader
# ============================================================================
def afsim_stdout_reader(proc):
    log("AFSIM stdout reader started")
    while state.running:
        try:
            line = proc.stdout.readline()
            if not line:
                break
            line = line.decode('utf-8', errors='replace').strip()
            if not line:
                continue
            parsed = parse_track_line(line)
            if parsed:
                if parsed["type"] == "track_count":
                    log(f"[AFSIM] Track count: {parsed['tracks']} at t={parsed['time']}", "AFSIM")
                elif parsed["type"] == "track":
                    t = parsed
                    state.update_track(t["track_id"], t["lat"], t["lon"], t["alt"],
                                     side=t.get("side","?"), speed=t.get("speed",0),
                                     heading=t.get("heading",0), sim_time=parsed.get("sim_time", 0))
                    log(f"[AFSIM] Track id={t['track_id']} lat={t['lat']:.4f} lon={t['lon']:.4f} "
                        f"alt={t['alt']:.0f}m spd={t.get('speed',0):.0f}m/s [{t.get('side','?')}]", "TRACK")
                elif parsed["type"] == "weapon_result":
                    t = parsed
                    state.record_engagement_result(t["target_id"], t["hit"], t.get("weapon", "unknown"))
                    log(f"[AFSIM] Weapon {'HIT' if t['hit'] else 'MISS'} on target {t['target_id']} "
                        f"t={t.get('time', 0):.0f}s weapon={t.get('weapon', 'unknown')}", "AFSIM")
                elif parsed["type"] == "time_marker":
                    log(f"[AFSIM] === T = {parsed['time']} ===", "AFSIM")
        except Exception as e:
            log(f"stdout reader error: {e}", "ERROR")
            break
    log("AFSIM stdout reader finished")


# ============================================================================
# Metrics Evaluation
# ============================================================================
def evaluate_run():
    """Evaluate the kill chain run and print metrics."""
    log("", "INFO")
    log("=" * 60, "INFO")
    log("KILL CHAIN PERFORMANCE EVALUATION", "INFO")
    log("=" * 60, "INFO")

    # Build sensor/weapon coverage grid (simplified)
    coverage_grid = {}
    # Just mark cells covered by sensors
    radar_lat, radar_lon = 38.0683, -117.2333
    for lat_i in range(-5, 6):
        for lon_i in range(-5, 6):
            dist = haversine_km(radar_lat + lat_i*0.01, radar_lon + lon_i*0.01,
                               radar_lat, radar_lon)
            coverage_grid[(lat_i+5, lon_i+5)] = max(0, 1 - dist/300)

    # Evaluate
    evaluator = MetricsEvaluator()
    summary = evaluator.evaluate(
        track_events=state.track_events,
        allocations=state.alloc_events,
        engagements=state.engagements,
        coverage_grid=coverage_grid if coverage_grid else None
    )

    # Print summary
    lines = evaluator.print_summary(summary).split("\n")
    for line in lines:
        log(line, "METRIC")

    # Save JSON report
    report_path = os.path.join(AFSIM_ROOT, "output", "kill_chain_metrics.json")
    import json as jsonmod
    report = {
        "timestamp": datetime.now().isoformat(),
        "sim_duration_sec": 180,
        "total_tracks": len(state.tracks),
        "total_allocations": len(state.alloc_events),
        "metrics": summary.to_dict(),
        "per_allocations": [
            {
                "target_id": a.target_id,
                "sensor_id": a.sensor_id,
                "weapon_id": a.weapon_id,
                "priority_score": a.priority_score,
                "decision_time_sec": a.decision_time_sec,
                "intercept_time_sec": a.intercept_time_sec
            }
            for a in state.alloc_events
        ]
    }
    with open(report_path, "w") as f:
        jsonmod.dump(report, f, indent=2)
    log(f"Metrics report saved: {report_path}", "INFO")
    log("", "INFO")

    return summary


# ============================================================================
# Main
# ============================================================================
def main():
    # Clear log
    with open(LOG_FILE, "w") as f:
        f.write("")

    log("=" * 60, "INFO")
    log("Kill Chain Simulation - MILP Allocation + Metrics", "INFO")
    log("=" * 60, "INFO")

    # Start pipe server
    pipe_thread = threading.Thread(target=pipe_server, daemon=True)
    pipe_thread.start()
    log("Pipe server started")

    # Start kill chain/MILP loop
    kc_thread = threading.Thread(target=kill_chain_loop, daemon=True)
    kc_thread.start()
    log("MILP decision loop started")

    # Spawn AFSIM
    log(f"Spawning AFSIM: {AFSIM_BIN}", "INFO")
    log(f"Scenario: {SCENARIO_FILE}", "INFO")

    afsim_proc = subprocess.Popen(
        [AFSIM_BIN, SCENARIO_FILE],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=AFSIM_ROOT,
        text=False
    )
    log(f"AFSIM started (PID={afsim_proc.pid})", "INFO")

    # Start stdout reader
    reader_thread = threading.Thread(target=afsim_stdout_reader, args=(afsim_proc,), daemon=True)
    reader_thread.start()

    # Wait for AFSIM
    try:
        retcode = afsim_proc.wait()
        log(f"AFSIM exited with code {retcode}", "INFO")
    except KeyboardInterrupt:
        log("Interrupted - killing AFSIM", "INFO")
        afsim_proc.terminate()
        afsim_proc.wait()
    finally:
        state.running = False

    log("Simulation complete", "INFO")
    log(f"Final state: {len(state.tracks)} tracks, {len(state.alloc_events)} allocation decisions", "INFO")

    # Evaluate
    evaluate_run()


if __name__ == "__main__":
    main()

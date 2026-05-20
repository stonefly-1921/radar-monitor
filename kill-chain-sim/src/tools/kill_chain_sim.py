#!/usr/bin/env python
"""
Kill Chain Simulator & Validator
================================

Reads AFSIM tracks from SHM (written by afsim_bridge.py),
runs MILP kill chain allocation, and logs the reasoning behind each decision.

No DIS required — validates kill chain logic in isolation.
AFSIM provides: track lat/lon/alt/vel/hdg for hostile targets.
Python provides: blue force structure (sensors + weapons) + allocation logic.

Usage:
    python -m src.tools.kill_chain_sim --shm kill_chain_shm --interval 5.0
"""

import argparse
import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.shared_mem.shm_client import ShmClient, TrackEntry, track_to_dict
from src.research.algorithms.milp_allocator import (
    MilpAllocator, Target, Sensor, Weapon,
    Allocation, SolveResult, SolveStatus
)


# =============================================================================
# Blue Force Definition (static — replaces DIS-fed entity tracker)
# =============================================================================

BLUE_SENSORS = [
    Sensor(id=1, range_km=300, mode="track", azimuth_fov_deg=60, elevation_fov_deg=30),
    Sensor(id=2, range_km=200, mode="search", azimuth_fov_deg=120, elevation_fov_deg=45),
]

BLUE_WEAPONS = [
    Weapon(id=1, range_km=250, kill_probability=0.85, max_target_speed_kts=3000, type="sam"),
    Weapon(id=2, range_km=150, kill_probability=0.75, max_target_speed_kts=2500, type="sam"),
    Weapon(id=3, range_km=80, kill_probability=0.90, max_target_speed_kts=2000, type="aaa"),
]


# =============================================================================
# Track → Target Mapper
# =============================================================================

def track_to_target(track: TrackEntry, blue_sensor_lat: float = 38.0,
                    blue_sensor_lon: float = -117.0) -> Target:
    """Convert SHM TrackEntry to MILP Target."""
    d = track_to_dict(track)

    # Range from blue sensor to target (Haversine km)
    range_km = haversine_km(
        blue_sensor_lat, blue_sensor_lon,
        d["lat"], d["lon"]
    )

    # Velocity: knots (AFSIM reports m/s)
    vel_kts = d["velocity"] * 1.94384

    # Altitude: ft
    alt_ft = d["altitude"] * 3.28084

    # Priority: based on altitude (lower = higher priority for terminal defense)
    # and speed (faster = higher priority)
    alt_factor = 1.0 + (30000 - alt_ft) / 30000  # higher priority for low-flying
    vel_factor = 1.0 + vel_kts / 2000
    base_priority = 5.0
    priority = base_priority * alt_factor * vel_factor

    # Target type from track.type (0=AIRCRAFT, 1=MISSILE, 2=UCAV)
    type_map = {0: "aircraft", 1: "missile", 2: "ucav"}
    target_type = type_map.get(d["type"], "aircraft")

    return Target(
        id=d["track_id"],
        priority=min(priority, 10.0),  # cap at 10
        velocity_kts=vel_kts,
        type=target_type,
        lat=d["lat"],
        lon=d["lon"],
        altitude_ft=alt_ft,
        range_to_sensors={s.id: range_km for s in BLUE_SENSORS}
    )


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    # Clamp to valid range for atan2 to avoid 0/0 edge case
    a = max(0.0, min(1.0, a))
    dist = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    # Clamp very small distances to a minimum — target at exact sensor location
    return max(dist, 0.1)


# =============================================================================
# Kill Chain Evaluator (lightweight)
# =============================================================================

@dataclass
class KillChainDecision:
    timestamp: float
    cycle: int
    tracks_seen: List[int]
    allocations: List[Allocation]
    unassigned: List[int]
    solve_time_sec: float
    status: SolveStatus


class KillChainSimulator:
    """Runs kill chain allocation cycles against SHM tracks."""

    def __init__(self, shm_name: str = "kill_chain_shm",
                 blue_sensor_lat: float = 38.0,
                 blue_sensor_lon: float = -117.0,
                 alloc_interval: float = 5.0,
                 time_limit: float = 10.0):
        self.shm_name = shm_name
        self.blue_sensor_lat = blue_sensor_lat
        self.blue_sensor_lon = blue_sensor_lon
        self.alloc_interval = alloc_interval
        self.allocator = MilpAllocator(time_limit_sec=time_limit, verbose=False)

        self.shm: Optional[ShmClient] = None
        self.decisions: List[KillChainDecision] = []
        self.cycle = 0
        self.last_alloc_time = 0.0
        self.start_time: Optional[float] = None

    def connect(self) -> bool:
        self.shm = ShmClient(self.shm_name)
        ok = self.shm.connect()
        if ok:
            print(f"[Sim] Connected to SHM: {self.shm_name}")
        return ok

    def _read_tracks(self) -> List[TrackEntry]:
        """Read latest round-robin tracks from SHM."""
        if not self.shm:
            return []
        header = self.shm._read_header()
        if not header or header.magic != 0x4B494C4C:
            return []

        # Read all 512 round-robin slots, return most recent entries
        from src.core.shared_mem.shm_client import TRACKS_OFFSET, TRACK_SIZE
        seen = {}
        count = min(header.track_count, 512)

        for i in range(count):
            off = TRACKS_OFFSET + i * TRACK_SIZE
            t = self.shm._read_track(off)
            if t and t.track_id != 0:
                # Deduplicate by track_id, keep highest index = most recent
                if t.track_id not in seen:
                    seen[t.track_id] = t

        return list(seen.values())

    def run_allocation_cycle(self) -> KillChainDecision:
        """Run one allocation cycle."""
        self.cycle += 1
        now = time.time()
        elapsed = now - (self.start_time or now)

        tracks = self._read_tracks()
        track_ids = [t.track_id for t in tracks]

        print(f"\n[Sim] === Cycle {self.cycle} (T+{elapsed:.1f}s) ===")
        print(f"[Sim] Tracks in SHM: {track_ids}")

        if not tracks:
            print("[Sim] No tracks available")
            return KillChainDecision(
                timestamp=elapsed, cycle=self.cycle,
                tracks_seen=[], allocations=[],
                unassigned=[], solve_time_sec=0, status=SolveStatus.OPTIMAL
            )

        # Convert tracks to targets
        targets = []
        for t in tracks:
            tgt = track_to_target(t, self.blue_sensor_lat, self.blue_sensor_lon)
            targets.append(tgt)
            print(f"[Sim]   Target {tgt.id}: type={tgt.type}, alt={tgt.altitude_ft:.0f}ft, "
                  f"vel={tgt.velocity_kts:.0f}kts, range={list(tgt.range_to_sensors.values())[0]:.0f}km, "
                  f"priority={tgt.priority:.1f}")

        # Filter targets by sensor coverage
        in_range = []
        out_of_range = []
        for tgt in targets:
            covered = any(r <= s.range_km
                          for s, r in [(s, tgt.range_to_sensors.get(s.id, 9999)) for s in BLUE_SENSORS])
            if covered:
                in_range.append(tgt)
            else:
                out_of_range.append(tgt)

        if out_of_range:
            for tgt in out_of_range:
                r = list(tgt.range_to_sensors.values())[0]
                print(f"[Sim]   OUT OF RANGE: Target {tgt.id} at {r:.0f}km "
                      f"(max {max(s.range_km for s in BLUE_SENSORS)}km)")

        if not in_range:
            print("[Sim] No targets in sensor coverage — skipping allocation")
            return KillChainDecision(
                timestamp=elapsed, cycle=self.cycle,
                tracks_seen=track_ids, allocations=[],
                unassigned=track_ids, solve_time_sec=0, status=SolveStatus.OPTIMAL
            )

        # Filter weapons by target speed
        weapons = [w for w in BLUE_WEAPONS
                   if all(t.velocity_kts <= w.max_target_speed_kts for t in in_range)]

        if not weapons:
            print(f"[Sim] No weapons can intercept target speeds — using all weapons")
            weapons = BLUE_WEAPONS

        print(f"[Sim] Running MILP: {len(in_range)} targets, {len(BLUE_SENSORS)} sensors, "
              f"{len(weapons)} weapons")

        result = self.allocator.solve(in_range, BLUE_SENSORS, weapons)

        print(f"[Sim] Solve: {result.status.value} ({result.solve_time_sec:.3f}s), "
              f"{len(result.allocations)} allocated, "
              f"{len(result.unassigned_targets)} unassigned")

        for alloc in result.allocations:
            sensor = next(s for s in BLUE_SENSORS if s.id == alloc.sensor_id)
            weapon = next(w for w in weapons if w.id == alloc.weapon_id)
            tgt = next(t for t in targets if t.id == alloc.target_id)
            print(f"[Sim]   ALLOCATE: Tgt {tgt.id}({tgt.type}) → "
                  f"Sensor{sensor.id}({sensor.mode}) + Weapon{weapon.id}({weapon.type}) "
                  f"| P={alloc.priority_score:.2f} KP={alloc.kill_probability:.0%} "
                  f"t_intercept={alloc.intercept_time_sec:.1f}s")

        for uid in result.unassigned_targets:
            tgt = next(t for t in targets if t.id == uid)
            print(f"[Sim]   UNASSIGNED: Tgt {tgt.id}({tgt.type}) — "
                  f"no sensor+weapon coverage")

        decision = KillChainDecision(
            timestamp=elapsed, cycle=self.cycle,
            tracks_seen=track_ids,
            allocations=result.allocations,
            unassigned=result.unassigned_targets,
            solve_time_sec=result.solve_time_sec,
            status=result.status
        )
        self.decisions.append(decision)
        return decision

    def run_loop(self, duration: Optional[float] = None):
        """Main simulation loop."""
        print(f"[Sim] Kill Chain Simulator starting")
        print(f"[Sim] Blue sensors: {[(s.id, s.mode, s.range_km) for s in BLUE_SENSORS]}")
        print(f"[Sim] Blue weapons: {[(w.id, w.type, w.range_km, w.kill_probability) for w in BLUE_WEAPONS]}")
        print(f"[Sim] Allocation interval: {self.alloc_interval}s")
        print(f"[Sim] MILP time limit: {self.allocator.time_limit_sec}s")
        self.start_time = time.time()
        self.last_alloc_time = 0

        try:
            while True:
                now = time.time()
                elapsed = now - self.start_time

                if duration and elapsed >= duration:
                    print(f"\n[Sim] Duration {duration}s reached — stopping")
                    break

                if elapsed - self.last_alloc_time >= self.alloc_interval:
                    self.run_allocation_cycle()
                    self.last_alloc_time = elapsed

                time.sleep(0.5)

        except KeyboardInterrupt:
            print(f"\n[Sim] Interrupted after {self.cycle} cycles")

        self._print_summary()

    def _print_summary(self):
        total_alloc = sum(len(d.allocations) for d in self.decisions)
        total_unassign = sum(len(d.unassigned) for d in self.decisions)
        print(f"\n[Sim] === SUMMARY ===")
        print(f"[Sim] Cycles run: {self.cycle}")
        print(f"[Sim] Total allocations: {total_alloc}")
        print(f"[Sim] Total unassigned: {total_unassign}")
        if self.decisions:
            avg_solve = sum(d.solve_time_sec for d in self.decisions) / len(self.decisions)
            print(f"[Sim] Avg MILP solve time: {avg_solve*1000:.1f}ms")


def main():
    parser = argparse.ArgumentParser(description="Kill Chain Simulator")
    parser.add_argument("--shm", default="kill_chain_shm",
                        help="SHM name (default: kill_chain_shm)")
    parser.add_argument("--interval", type=float, default=5.0,
                        help="Allocation interval in seconds (default: 5.0)")
    parser.add_argument("--duration", type=float, default=None,
                        help="Run for N seconds then stop (default: run forever)")
    parser.add_argument("--time-limit", type=float, default=10.0,
                        help="MILP solver time limit in seconds (default: 10)")
    args = parser.parse_args()

    sim = KillChainSimulator(
        shm_name=args.shm,
        alloc_interval=args.interval,
        time_limit=args.time_limit,
    )

    if not sim.connect():
        print("[Sim] Failed to connect to SHM — is afsim_bridge.py running?")
        sys.exit(1)

    sim.run_loop(duration=args.duration)


if __name__ == "__main__":
    main()

"""
多目标杀伤链 Python 决策控制器
- 威胁评估（距离×速度×类型权重）
- 武器-目标分配（饱和判断）
- 传感器控制决策（模式+数据率）
- 输出：事件日志 + 统计摘要

AFSIM: kill_chain_np_multi.txt
Python: polls afsim_track_out.txt
        writes FIRE commands -> kill_chain_np_cmd.txt
        writes SENSOR commands -> sensor_cmd.txt

Usage:
    python kill_chain_np_fire_controller.py --scenario kill_chain_np_multi.txt
"""

import argparse
import sys
import time
import re
import os
import math
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
AFSIM_BIN = "D:/afsim-2.9.0-win64/bin/mission.exe"
WORKSPACE = Path("C:/Users/15041/.openclaw/workspace/kill-chain-sim")
TRACK_FILE = WORKSPACE / "afsim_track_out.txt"
CMD_FILE = WORKSPACE / "kill_chain_np_cmd.txt"
ACK_FILE = WORKSPACE / "kill_chain_np_ack.txt"
SENSOR_FILE = WORKSPACE / "sensor_cmd.txt"
SCENARIO_DEFAULT = "C:/Users/15041/.openclaw/workspace/kill-chain-sim/src/sim/kill_chain_np_multi.txt"

# EVT file: AFSIM resolves "output/<name>.evt" relative to the scenario file's directory
# (confirmed: mission.log shows "Event output file: output/kill_chain_np_multi.evt"
#  but file is created in <scenario_dir>/output/, not CWD).
# For scenario "src/sim/kill_chain_np_multi.txt" -> <scenario_dir>/output/kill_chain_np_multi.evt
def _evt_file_from_scenario(scenario_path: str) -> Path:
    """Derive EVT path: <scenario_dir>/output/<scenario_name>.evt"""
    s = Path(scenario_path)
    evt_name = s.name.replace('.txt', '.evt')
    return s.parent / "output" / evt_name

EVT_FILE = _evt_file_from_scenario(SCENARIO_DEFAULT)

# Regex: matches "TRACK: id=X lat=Y lon=Z alt=A vel=S hdg=H"
TRACK_RE = re.compile(
    r"TRACK:\s*id=(\d+)\s+lat=([-\d.]+)\s+lon=([-\d.]+)\s+alt=([-\d.]+)\s+vel=([-\d.]+)\s+hdg=([-\d.]+)"
)

# Radar position (degrees) — used for distance calc
RADAR_LAT = 38.0 + 4/60 + 6/3600      # 38:04:06n
RADAR_LON = -(117.0 + 14/60)           # 117:14:00w -> negative

# Weapon params
WEAPON_RANGE_M = 30000.0               # 30km max range

# Threat weights — per spec
DIST_WEIGHT = 1.0
SPEED_WEIGHT = 0.5
TYPE_FACTOR_ASM = 1.0
TYPE_FACTOR_FIGHTER = 0.7
TYPE_FACTOR_UAV = 0.5

# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Track:
    track_id: int
    lat: float
    lon: float
    alt: float     # meters
    vel: float     # m/s
    hdg: float     # degrees
    first_seen: float = 0.0
    last_seen: float = 0.0
    fired_upon: bool = False   # already had a weapon allocated

@dataclass
class Weapon:
    name: str
    available: int
    range_max: float

@dataclass
class Decision:
    fires: List[str] = field(default_factory=list)
    sensor_mode: str = "SEARCH"
    sensor_track: Optional[int] = None


# ─────────────────────────────────────────────────────────────────────────────
# Threat assessor
# ─────────────────────────────────────────────────────────────────────────────
def haversine_m(lat1, lon1, lat2, lon2):
    """Return great-circle distance in meters."""
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def estimate_target_type(track: Track) -> str:
    """Infer target type from altitude and speed heuristics."""
    if track.alt < 2000.0 and track.vel < 400.0:
        return "ASM"
    elif track.vel > 500.0:
        return "FIGHTER"
    else:
        return "UAV"


def calc_threat(track: Track, radar_lat: float, radar_lon: float) -> float:
    """
    Per-spec formula:
    threat = DIST_WEIGHT * (1/dist_km) + SPEED_WEIGHT * speed + type_factor

    type_factor:
      - ASM (anti-ship missile): 1.0
      - fighter: 0.7
      - UAV: 0.5
    """
    dist_m = haversine_m(radar_lat, radar_lon, track.lat, track.lon)
    dist_km = dist_m / 1000.0
    ttype = estimate_target_type(track)

    type_factor = {
        "ASM": TYPE_FACTOR_ASM,
        "FIGHTER": TYPE_FACTOR_FIGHTER,
        "UAV": TYPE_FACTOR_UAV,
    }.get(ttype, TYPE_FACTOR_FIGHTER)

    # threat = dist_weight * (1/dist_km) + speed_weight * speed + type_factor
    threat = (DIST_WEIGHT * (1.0 / max(dist_km, 0.1))
              + SPEED_WEIGHT * track.vel
              + type_factor)
    return threat


# ─────────────────────────────────────────────────────────────────────────────
# Decision engine
# ─────────────────────────────────────────────────────────────────────────────
class KillChainController:
    def __init__(self, scenario_path: str):
        self.scenario_path = scenario_path
        self.afsim = None

        self.tracks: Dict[int, Track] = {}
        self.weapons = [
            Weapon(name="aim120_sim_1", available=1, range_max=WEAPON_RANGE_M),
            Weapon(name="aim120_sim_2", available=1, range_max=WEAPON_RANGE_M),
            Weapon(name="aim120_sim_3", available=1, range_max=WEAPON_RANGE_M),
            Weapon(name="aim120_sim_4", available=1, range_max=WEAPON_RANGE_M),
        ]
        self.used_weapons: set = set()      # weapon names already used
        self.fired_upon_tracks: set = set() # track_ids already fired upon

        self.sensor_mode = "SEARCH"
        self.sensor_track: Optional[int] = None

        self.pending_fires: List[str] = []

        # File state (dedup writes)
        self.last_track_content = ""
        self.last_cmd = ""
        self.last_sensor_cmd = ""

        # Timing
        self.start_time: Optional[float] = None
        self.decision_times: List[float] = []

        # Stats
        self.decisions_made = 0
        self._seen_evt_lines: set = set()
        self.kill_count = 0
        self.miss_count = 0

    # ── File I/O ─────────────────────────────────────────────────────────────

    def _write_file(self, path: Path, content: str):
        """Write content to file, skip if unchanged."""
        try:
            path.write_text(content, encoding="utf-8")
        except Exception as e:
            print(f"  [FILE] Write error {path}: {e}")

    def write_cmd(self, lines: List[str]):
        content = "\n".join(lines) + "\n"
        if content == self.last_cmd:
            return
        self._write_file(CMD_FILE, content)
        self.last_cmd = content

    def write_sensor(self, mode: str, track_id: Optional[int] = None):
        if mode == "SEARCH":
            cmd = "SENSOR:radar1:SEARCH"
        elif mode == "TRACK" and track_id is not None:
            cmd = f"SENSOR:radar1:TRACK:radar1:{track_id}"
        elif mode == "HIGH_RATE":
            cmd = "SENSOR:radar1:HIGH_RATE"
        else:
            return
        if cmd == self.last_sensor_cmd:
            return
        self._write_file(SENSOR_FILE, cmd + "\n")
        self.last_sensor_cmd = cmd

    def clear_cmd(self):
        """Clear command file."""
        self._write_file(CMD_FILE, "")
        self.last_cmd = ""

    # ── Track parsing ─────────────────────────────────────────────────────────

    def parse_tracks(self, content: str):
        lines = content.strip().split("\n")
        t_now = time.time()

        for line in lines:
            line = line.strip()
            if not line.startswith("TRACK:"):
                continue
            m = TRACK_RE.search(line)
            if not m:
                continue
            try:
                tid = int(m.group(1))
                lat = float(m.group(2))
                lon = float(m.group(3))
                alt = float(m.group(4))
                vel = float(m.group(5))
                hdg = float(m.group(6))
            except ValueError:
                continue

            if tid not in self.tracks:
                self.tracks[tid] = Track(tid, lat, lon, alt, vel, hdg,
                                          first_seen=t_now, last_seen=t_now)
            else:
                self.tracks[tid].lat = lat
                self.tracks[tid].lon = lon
                self.tracks[tid].alt = alt
                self.tracks[tid].vel = vel
                self.tracks[tid].hdg = hdg
                self.tracks[tid].last_seen = t_now

    # ── Decision logic ───────────────────────────────────────────────────────

    def decide(self) -> Decision:
        """
        Per-spec:
        1. Filter out-of-range (>30km) targets
        2. Sort by threat (highest first)
        3. Greedy allocate one weapon per target
        4. Saturation: if weapons < targets, only assign to top-priority targets
        5. Sensor mode decisions
        """
        t0 = time.time()
        decision = Decision()

        # Available weapons
        available_weapons = [w for w in self.weapons if w.name not in self.used_weapons]
        num_available = len(available_weapons)

        # Step 1: build live track list (filter out fired-upon and out-of-range)
        live_tracks: Dict[int, Track] = {}
        for tid, tr in self.tracks.items():
            if tid in self.fired_upon_tracks:
                continue
            dist = haversine_m(RADAR_LAT, RADAR_LON, tr.lat, tr.lon)
            if dist > WEAPON_RANGE_M:
                continue
            live_tracks[tid] = tr

        # Step 2: threat scoring and sort
        scored = []
        for tid, tr in live_tracks.items():
            threat = calc_threat(tr, RADAR_LAT, RADAR_LON)
            dist = haversine_m(RADAR_LAT, RADAR_LON, tr.lat, tr.lon)
            ttype = estimate_target_type(tr)
            scored.append((threat, tid, tr, dist, ttype))

        scored.sort(key=lambda x: -x[0])  # highest threat first

        # Step 3: print decision header + per-track info
        sim_t = self._sim_t()
        print(f"\n[DECISION] t={sim_t:.1f}s | tracks={len(live_tracks)} | weapons={num_available} available")
        for threat, tid, tr, dist, ttype in scored:
            print(f"  track {tid} ({ttype}, d={dist/1000:.1f}km, v={tr.vel:.0f}m/s) -> threat={threat:.2f}")

        # Step 4: saturation-aware weapon allocation
        # If weapons < targets, only allocate to top priority targets
        targets_to_assign = scored
        if num_available < len(scored):
            targets_to_assign = scored[:num_available]

        fires: List[str] = []
        for threat, tid, tr, dist, ttype in targets_to_assign:
            # Find first unused weapon
            for w in available_weapons:
                if w.name not in self.used_weapons and w.name not in [f.split(":")[1] for f in fires]:
                    fires.append(f"FIRE:{w.name}:radar1:{tid}")
                    self.used_weapons.add(w.name)
                    self.fired_upon_tracks.add(tid)
                    print(f"    -> FIRE:{w.name}:radar1:{tid}")
                    break

        decision.fires = fires

        # Step 5: sensor mode
        if not live_tracks:
            decision.sensor_mode = "SEARCH"
            self.sensor_mode = "SEARCH"
            decision.sensor_track = None
            self.sensor_track = None
        else:
            top = scored[0] if scored else None
            top_tid = top[1] if top else None
            if len(live_tracks) >= 3:
                decision.sensor_mode = "HIGH_RATE"
                self.sensor_mode = "HIGH_RATE"
            else:
                decision.sensor_mode = "TRACK"
                self.sensor_mode = "TRACK"
            decision.sensor_track = top_tid
            self.sensor_track = top_tid

        self.decisions_made += 1
        self.decision_times.append(time.time() - t0)
        return decision

    def _sim_t(self) -> float:
        """Estimate simulation time from track file timestamps vs wall clock."""
        # Read current track count line for time
        try:
            if TRACK_FILE.exists():
                first_line = TRACK_FILE.read_text(encoding="utf-8").split("\n")[0]
                if "time=" in first_line:
                    t_str = first_line.split("time=")[1].strip()
                    return float(t_str)
        except:
            pass
        return 0.0

    # ── EVT parsing ───────────────────────────────────────────────────────────

    def parse_evt_for_kills(self):
        """Read .evt file, count new kills/misses."""
        if not Path(EVT_FILE).exists():
            return
        try:
            content = Path(EVT_FILE).read_text(encoding="utf-8")
        except OSError:
            return

        # Join continuation lines: backslash + newline → space
        content = content.replace(chr(92) + "\n", " ")

        for line in content.split("\n"):
            if not line.strip() or line in self._seen_evt_lines:
                continue
            if "WEAPON_HIT" in line and "Result:" in line and "KILLED" in line:
                self._seen_evt_lines.add(line)
                self.kill_count += 1
                print(f"  [KILLED] {line[:120]}")
            elif "WEAPON_MISSED" in line:
                self._seen_evt_lines.add(line)
                self.miss_count += 1
                print(f"  [MISSED] {line[:120]}")

    # ── Poll tracks (no decision, no writes) ─────────────────────────────────

    def poll(self):
        if not TRACK_FILE.exists():
            return
        try:
            mtime = TRACK_FILE.stat().st_mtime
        except OSError:
            return
        try:
            content = TRACK_FILE.read_text(encoding="utf-8")
        except OSError:
            return
        if content != self.last_track_content:
            self.last_track_content = content
            self.parse_tracks(content)

    # ── Wait for ACK ─────────────────────────────────────────────────────────

    def wait_for_ack(self, timeout: float = 30.0) -> bool:
        """Wait for ACK file to appear with 'ACK' content."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.afsim and self.afsim.poll() is not None:
                # AFSIM exited
                return False
            try:
                if ACK_FILE.exists():
                    content = ACK_FILE.read_text(encoding="utf-8").strip()
                    if content == "ACK":
                        ACK_FILE.unlink()
                        return True
            except OSError:
                pass
            time.sleep(0.05)
        return False

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        print(f"[KC] Starting: {self.scenario_path}")
        print(f"[KC] Output EVT: {EVT_FILE}")

        # Clean slate
        for f in [CMD_FILE, SENSOR_FILE, ACK_FILE]:
            if f.exists():
                try:
                    f.unlink()
                except:
                    pass

        import subprocess
        # AFSIM resolves relative paths (log_file, output/, event_output) from WORKSPACE root.
        # Run from WORKSPACE with relative scenario path.
        # Note: the scenario file itself contains "realtime" so no -rt flag needed.
        scenario_name = str(Path(self.scenario_path).relative_to(WORKSPACE))
        self.afsim = subprocess.Popen(
            [AFSIM_BIN, scenario_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(WORKSPACE)
        )

        self.start_time = time.time()
        evt_check_interval = 5.0
        last_evt_check = 0.0

        try:
            while True:
                self.poll()

                now = time.time()
                if now - last_evt_check > evt_check_interval:
                    self.parse_evt_for_kills()
                    last_evt_check = now

                if self.afsim.poll() is not None:
                    self.poll()
                    print(f"\n[KC] AFSIM exited: {self.afsim.returncode}")
                    break

                # Make a decision
                decision = self.decide()

                if decision.fires:
                    # Batch write ALL fire commands at once
                    self.write_cmd(decision.fires)
                    for f in decision.fires:
                        print(f"  [FIRE] {f}")
                    self.write_sensor(decision.sensor_mode, decision.sensor_track)

                    # Wait for ACK
                    ack_ok = self.wait_for_ack()
                    if not ack_ok:
                        print(f"  [ACK] Timeout waiting for ACK, AFSIM may have exited")
                        break
                else:
                    self.write_sensor(decision.sensor_mode, decision.sensor_track)
                    time.sleep(0.1)

        except KeyboardInterrupt:
            print("\n[KC] Interrupted")
        finally:
            if self.afsim and self.afsim.poll() is None:
                self.afsim.terminate()
                try:
                    self.afsim.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.afsim.kill()

        # Final EVT parse
        self.parse_evt_for_kills()
        self.print_summary()

    def print_summary(self):
        total_tracks = len(self.tracks)
        fired_count = len(self.fired_upon_tracks)
        killed_count = self.kill_count
        missed_count = self.miss_count
        # Tracks that were neither killed nor missed = leaked
        leak_count = total_tracks - killed_count - missed_count

        dt = self.decision_times
        avg_ms = (sum(dt) / len(dt) * 1000) if dt else 0
        max_ms = (max(dt) * 1000) if dt else 0
        min_ms = (min(dt) * 1000) if dt else 0

        print("\n" + "=" * 60)
        print("  杀伤链统计摘要")
        print("=" * 60)
        print(f"  目标总数: {total_tracks}")
        print(f"  拦截弹发射: {fired_count}")
        print(f"  命中: {killed_count}")
        print(f"  漏网(已判定): {missed_count}")
        print(f"  漏网(未判定): {leak_count}")
        print(f"  拦截率: {killed_count/max(total_tracks,1)*100:.0f}%")
        print(f"  决策耗时: min={min_ms:.1f}ms max={max_ms:.1f}ms avg={avg_ms:.1f}ms")
        print("=" * 60)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Kill Chain Controller")
    parser.add_argument("--scenario", default=SCENARIO_DEFAULT)
    args = parser.parse_args()

    ctrl = KillChainController(args.scenario)
    ctrl.run()


if __name__ == "__main__":
    main()

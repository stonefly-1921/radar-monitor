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
SENSOR_FILE = WORKSPACE / "sensor_cmd.txt"
SCENARIO_DEFAULT = "C:/Users/15041/.openclaw/workspace/kill-chain-sim/src/sim/kill_chain_np_multi.txt"

# Regex: matches "TRACK: id=X lat=Y lon=Z alt=A vel=S hdg=H"
TRACK_RE = re.compile(
    r"TRACK:\s*id=(\d+)\s+lat=([-\d.]+)\s+lon=([-\d.]+)\s+alt=([-\d.]+)\s+vel=([-\d.]+)\s+hdg=([-\d.]+)"
)

# EVT event regexes
EVT_HIT_RE = re.compile(r"WEAPON_HIT\s+(\S+)\s+(\S+).*Result:\s+KILLED")
EVT_MISS_RE = re.compile(r"WEAPON_MISSED\s+(\S+)\s+(\S+)")
EVT_FIRE_RE = re.compile(r"WEAPON_FIRED\s+(\S+)\s+(\S+)\s+(\S+)")

# Radar position (degrees) — used for distance calc
RADAR_LAT = 38.0 + 4/60 + 6/3600      # 38:04:06n
RADAR_LON = -(117.0 + 14/60)           # 117:14:00w -> negative

# Weapon params
WEAPON_RANGE_M = 30000.0               # 30km max range

# Threat weights
WEIGHT_DISTANCE = 1.0
WEIGHT_SPEED = 0.5
WEIGHT_TYPE_ASM = 1.0
WEIGHT_TYPE_FIGHTER = 0.7


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

@dataclass
class Weapon:
    name: str
    available: int
    range_max: float
    fired: int = 0

@dataclass
class Decision:
    fires: List[str] = field(default_factory=list)     # ["FIRE:aim120_sim:radar1:3", ...]
    sensor_mode: str = "TRACK"                          # SEARCH / TRACK / HIGH_RATE
    sensor_track: Optional[int] = None


# ─────────────────────────────────────────────────────────────────────────────
# Threat assessor
# ─────────────────────────────────────────────────────────────────────────────
def haversine_m(lat1, lon1, lat2, lon2):
    """Return great-circle distance in meters."""
    import math
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
    return "FIGHTER"


def calc_threat(track: Track, radar_lat: float, radar_lon: float) -> float:
    dist_m = haversine_m(radar_lat, radar_lon, track.lat, track.lon)
    dist_km = dist_m / 1000.0
    ttype = estimate_target_type(track)

    type_weight = WEIGHT_TYPE_ASM if ttype == "ASM" else WEIGHT_TYPE_FIGHTER

    # threat = type_weight * (100/dist_km) + speed_weight * track.vel
    threat = type_weight * (100.0 / max(dist_km, 1.0)) + WEIGHT_SPEED * track.vel / 100.0
    return threat


# ─────────────────────────────────────────────────────────────────────────────
# Decision engine
# ─────────────────────────────────────────────────────────────────────────────
class KillChainController:
    def __init__(self, scenario_path: str):
        self.scenario_path = scenario_path
        self.afsim = None

        # Tracks
        self.tracks: Dict[int, Track] = {}
        self.fired_tracks: set = set()     # track_ids already fired upon
        self.used_weapons: set = set()      # weapon names already used

        # Stats
        self.decisions_made = 0
        self._seen_evt_lines: set = set()   # lines already counted (persistent)
        self.kill_count = 0
        self.miss_count = 0

        self.weapons = [
            Weapon(name="aim120_sim_1", available=1, range_max=WEAPON_RANGE_M),
            Weapon(name="aim120_sim_2", available=1, range_max=WEAPON_RANGE_M),
            Weapon(name="aim120_sim_3", available=1, range_max=WEAPON_RANGE_M),
            Weapon(name="aim120_sim_4", available=1, range_max=WEAPON_RANGE_M),
        ]

        # Sensor state
        self.sensor_mode = "SEARCH"
        self.sensor_track: Optional[int] = None

        # Pending fire command (for ACK-based dispatch in run())
        self.pending_fire: Optional[str] = None

        # File state
        self.last_track_content = ""
        self.last_cmd = ""
        self.last_sensor_cmd = ""

        # Timing
        self.start_time: Optional[float] = None
        self.decision_times: List[float] = []

        # Stats
        self.decisions_made = 0

    # ── File I/O ─────────────────────────────────────────────────────────────

    def write_cmd(self, lines: List[str]):
        """Write newline-separated commands to FIRE file."""
        content = "\n".join(lines) + "\n"
        if content == self.last_cmd:
            return
        try:
            CMD_FILE.write_text(content, encoding="utf-8")
            self.last_cmd = content
        except Exception as e:
            print(f"  [CMD] Write error: {e}")

    def write_sensor(self, mode: str, track_id: Optional[int] = None):
        if mode == "SEARCH":
            cmd = f"SENSOR:radar1:SEARCH"
        elif mode == "TRACK" and track_id is not None:
            cmd = f"SENSOR:radar1:TRACK:radar1:{track_id}"
        elif mode == "HIGH_RATE":
            cmd = f"SENSOR:radar1:HIGH_RATE"
        else:
            return

        if cmd == self.last_sensor_cmd:
            return
        try:
            SENSOR_FILE.write_text(cmd + "\n", encoding="utf-8")
            self.last_sensor_cmd = cmd
            print(f"  [SENSOR] -> {cmd}")
        except Exception as e:
            print(f"  [SENSOR] Write error: {e}")

    # ── Track parsing ─────────────────────────────────────────────────────────

    def parse_tracks(self, content: str):
        """Parse TRACK lines, update self.tracks dict."""
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

    # ── Decision logic ────────────────────────────────────────────────────────

    def decide(self) -> Decision:
        """
        Full decision cycle:
        1. Prune tracks that are dead / off-screen
        2. Compute threat index for each track
        3. Filter by weapon range
        4. Greedy allocate weapons to highest-threat tracks
        5. Decide sensor mode
        """
        t0 = time.time()
        decision = Decision()

        live_tracks = {}
        for tid, tr in self.tracks.items():
            if tid in self.fired_tracks:
                continue
            dist = haversine_m(RADAR_LAT, RADAR_LON, tr.lat, tr.lon)
            if dist > WEAPON_RANGE_M * 1.2:   # allow 20% overshoot
                continue
            live_tracks[tid] = tr

        if not live_tracks:
            decision.sensor_mode = "SEARCH"
            self.sensor_mode = "SEARCH"
            self.sensor_track = None
            self.decision_times.append(time.time() - t0)
            return decision

        # Threat sort
        scored = [(calc_threat(tr, RADAR_LAT, RADAR_LON), tid, tr)
                  for tid, tr in live_tracks.items()]
        scored.sort(key=lambda x: -x[0])   # highest threat first

        # Weapon allocation
        total_weapons = sum(w.available for w in self.weapons)
        available = total_weapons - len(self.used_weapons)
        target_count = len(live_tracks)

        print(f"\n  [DECISION] t={self._sim_t():.1f}s | tracks={target_count} | weapons_avail={available}")
        for score, tid, tr in scored:
            dist = haversine_m(RADAR_LAT, RADAR_LON, tr.lat, tr.lon)
            ttype = estimate_target_type(tr)
            print(f"    track {tid} ({ttype}, d={dist/1000:.1f}km, v={tr.vel:.0f}m/s) -> threat={score:.2f}")

        # FIRE decisions: fire ONE weapon per decision cycle (next cycle fires the next)
        # This prevents multiple commands overwriting the file before cmd_reader can process them
        fires_allocated = 0
        for score, tid, tr in scored:
            if fires_allocated >= 1:   # only one fire per cycle
                break
            for w in self.weapons:
                if w.name not in self.used_weapons:
                    decision.fires.append(f"FIRE:{w.name}:radar1:{tid}")
                    self.used_weapons.add(w.name)
                    fires_allocated += 1
                    break

        # Sensor mode: track the highest-priority target if we have any
        top_tid = scored[0][1] if scored else None
        if top_tid != self.sensor_track:
            self.sensor_track = top_tid
            decision.sensor_mode = "TRACK"
            decision.sensor_track = top_tid
            self.sensor_mode = "TRACK"
        else:
            decision.sensor_mode = "TRACK" if top_tid else "SEARCH"
            decision.sensor_track = top_tid

        # High-rate when 3+ tracks
        if target_count >= 3:
            decision.sensor_mode = "HIGH_RATE"

        self.decisions_made += 1
        self.decision_times.append(time.time() - t0)
        return decision

    def _sim_t(self) -> float:
        """Estimate simulation time from first track seen."""
        if not self.tracks:
            return 0.0
        earliest = min(t.first_seen for t in self.tracks.values())
        return time.time() - (self.start_time or time.time()) + 1.0

    # ── Main loop ─────────────────────────────────────────────────────────────

    def poll(self):
        if not TRACK_FILE.exists():
            return
        try:
            mtime = TRACK_FILE.stat().st_mtime
            size = TRACK_FILE.stat().st_size
        except OSError:
            return

        try:
            content = TRACK_FILE.read_text(encoding="utf-8")
        except OSError:
            return

        if content != self.last_track_content:
            self.last_track_content = content
            self.parse_tracks(content)

            # Run decision
            dec = self.decide()

            # Set pending fire for run() loop to dispatch (with ACK)
            if dec.fires:
                self.pending_fire = dec.fires[0]  # one at a time
                self.sensor_mode = dec.sensor_mode
                self.sensor_track = dec.sensor_track
            else:
                self.pending_fire = None

            self.write_sensor(dec.sensor_mode, dec.sensor_track)

    def parse_evt_for_kills(self):
        """Read .evt file, count new kills/misses since last check.
        EVT uses backslash continuation, so strip \'s and join lines first.
        """
        evt_path = Path("C:/Users/15041/.openclaw/workspace/kill-chain-sim/src/sim/output/kill_chain_np_multi.evt")
        if not evt_path.exists():
            return
        try:
            content = evt_path.read_text(encoding="utf-8")
        except OSError:
            return

        # Join continuation lines (lines ending with \)
        content = content.replace("\\\n", " ")

        for line in content.split("\n"):
            if not line.strip():
                continue
            if line in self._seen_evt_lines:
                continue
            if "WEAPON_HIT" in line and "Result: KILLED" in line:
                self._seen_evt_lines.add(line)
                self.kill_count += 1
                print(f"  [KILLED] {line[:100]}")
            elif "WEAPON_MISSED" in line:
                self._seen_evt_lines.add(line)
                self.miss_count += 1
                print(f"  [MISSED] {line[:100]}")

    def run(self):
        TRACK_FILE = Path("C:/Users/15041/.openclaw/workspace/kill-chain-sim/afsim_track_out.txt")
        CMD_FILE = Path("C:/Users/15041/.openclaw/workspace/kill-chain-sim/kill_chain_np_cmd.txt")
        ACK_FILE = Path("C:/Users/15041/.openclaw/workspace/kill-chain-sim/kill_chain_np_ack.txt")
        SENSOR_FILE = Path("C:/Users/15041/.openclaw/workspace/kill-chain-sim/sensor_cmd.txt")
        AFSIM_BIN = "D:/afsim-2.9.0-win64/bin/mission.exe"

        print(f"[KC] Starting: {self.scenario_path}")
        print(f"[KC] Track file: {TRACK_FILE}")
        print(f"[KC] FIRE cmd: {CMD_FILE}")
        print(f"[KC] SENSOR cmd: {SENSOR_FILE}")

        for f in [CMD_FILE, SENSOR_FILE, ACK_FILE]:
            if f.exists():
                f.unlink()

        import subprocess
        self.afsim = subprocess.Popen(
            [AFSIM_BIN, "-rt", self.scenario_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(Path(self.scenario_path).resolve().parent)
        )

        self.start_time = time.time()
        evt_check_interval = 5.0
        last_evt_check = 0.0
        pending_fire_ack: Optional[str] = None

        try:
            while True:
                if pending_fire_ack is not None:
                    ack_content = ""
                    try:
                        ack_content = ACK_FILE.read_text(encoding="utf-8").strip()
                    except OSError:
                        pass

                    if ack_content == "ACK":
                        ACK_FILE.unlink()
                        print(f"  [ACK] {pending_fire_ack} confirmed")
                        pending_fire_ack = None
                        self.poll()
                    else:
                        time.sleep(0.05)
                        if self.afsim.poll() is not None:
                            self.poll()
                            print(f"\n[KC] AFSIM exit: {self.afsim.returncode}")
                            break
                        continue

                self.poll()

                now = time.time()
                if now - last_evt_check > evt_check_interval:
                    self.parse_evt_for_kills()
                    last_evt_check = now

                if self.pending_fire:
                    fire_cmd = self.pending_fire
                    self.pending_fire = None
                    self.write_cmd([fire_cmd])
                    tid = int(fire_cmd.split(":")[-1])
                    self.fired_tracks.add(tid)
                    wname = fire_cmd.split(":")[1]
                    self.used_weapons.add(wname)
                    print(f"  [FIRE] {fire_cmd}")
                    pending_fire_ack = wname
                    self.write_sensor(self.sensor_mode, self.sensor_track)
                else:
                    time.sleep(0.05)

                if self.afsim.poll() is not None:
                    self.poll()
                    print(f"\n[KC] AFSIM exit: {self.afsim.returncode}")
                    break

        except KeyboardInterrupt:
            print("\n[KC] Interrupted")
        finally:
            if self.afsim and self.afsim.poll() is None:
                self.afsim.terminate()
                try:
                    self.afsim.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.afsim.kill()

        self.print_summary()

    def print_summary(self):
        total_tracks = len(self.tracks)
        fired_count = len(self.fired_tracks)
        killed_count = self.kill_count
        missed_count = self.miss_count
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

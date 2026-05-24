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
KILL_RESULT_FILE = WORKSPACE / "kill_assessment_result.txt"
SCENARIO_DEFAULT = "C:/Users/15041/.openclaw/workspace/kill-chain-sim/src/sim/kill_chain_np_multi.txt"

# EVT file: AFSIM resolves "output/<name>.evt" relative to the scenario file's directory
# (confirmed: mission.log shows "Event output file: output/kill_chain_np_multi.evt"
#  but file is created in <scenario_dir>/output/, not CWD).
# For scenario "src/sim/kill_chain_np_multi.txt" -> <scenario_dir>/output/kill_chain_np_multi.evt
def _evt_file_from_scenario(scenario_path: str) -> Path:
    """Derive EVT path: <WORKSPACE>/output/<scenario_name>.evt
    AFSIM resolves 'output/' relative to WORKSPACE when cwd=WORKSPACE.
    """
    s = Path(scenario_path)
    evt_name = s.name.replace('.txt', '.evt')
    return WORKSPACE / "output" / evt_name

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
WEAPON_REENGAGE_TIMEOUT = 15.0         # seconds before allowing re-fire on same target

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
    killed: bool = False      # kill-assessment confirmed target destroyed

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
    # High-altitude stationary targets (e.g. AWACS at 8000m, vel=0) are high-value.
    # Give them a minimum type_factor boost so they aren't under-weighted.
    if track.alt >= 5000.0 and track.vel == 0.0:
        return "FIGHTER"  # Treat as fighter-equivalent for threat ranking
    if track.alt < 2000.0 and track.vel < 400.0:
        return "ASM"
    elif track.vel >= 200.0:  # 300 m/s fighter is well above 200 threshold
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
    # Stationary high-altitude targets (vel=0) still pose threat; use min floor for speed
    speed_contribution = max(track.vel, 200.0)  # floor at 200 m/s for vel=0 targets
    threat = (DIST_WEIGHT * (1.0 / max(dist_km, 0.1))
              + SPEED_WEIGHT * speed_contribution
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
            Weapon(name="aim120_sim_5", available=1, range_max=WEAPON_RANGE_M),
            Weapon(name="aim120_sim_6", available=1, range_max=WEAPON_RANGE_M),
        ]
        self.used_weapons: set = set()      # weapon names already used
        # P0-4: fired_upon_tracks -> tracks currently locked by an in-flight weapon
        # Value=None means weapon was just allocated (track is "busy" until ACK/confirmation)
        # Value=timestamp means weapon was fired, waiting for kill confirmation
        self.fired_upon_tracks: Dict[int, Optional[float]] = {}  # track_id -> None|fire_time

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
        self.fire_count = 0  # total FIREs sent (for summary)
        # P2-2: OODA loop timing
        self.fire_latencies: List[float] = []  # wall-clock seconds from track detection to FIRE decision

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

    def write_sensor(self, mode: str):
        # mode: SEARCH, TRACK, ILLUMINATE, or OFF
        if mode not in ("SEARCH", "TRACK", "ILLUMINATE", "OFF"):
            return
        cmd = f"SENSOR:radar1:{mode}"
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
        # P0-4: fired_upon_tracks is dict[track_id -> fire_time], re-engage after timeout
        sim_t = self._sim_t()
        live_tracks: Dict[int, Track] = {}
        for tid, tr in self.tracks.items():
            # Skip targets confirmed killed by weapon kill-assessment
            if tr.killed:
                continue
            # Check if recently fired upon (timeout-based re-engagement)
            if tid in self.fired_upon_tracks:
                fire_time = self.fired_upon_tracks[tid]
                # None sentinel means weapon was just allocated — skip this target (already allocated)
                if fire_time is None:
                    continue
                if sim_t - fire_time < WEAPON_REENGAGE_TIMEOUT:
                    continue  # still in cooldown, skip
                # Timeout expired: allow re-engagement, remove from dict
                del self.fired_upon_tracks[tid]
            dist = haversine_m(RADAR_LAT, RADAR_LON, tr.lat, tr.lon)
            if dist > WEAPON_RANGE_M:
                continue
            live_tracks[tid] = tr

        # Step 2: threat scoring and sort
        # P0-2: exclude ground/stationary targets (alt <= 100m AND vel <= 0)
        # P0-1: filter out targets beyond weapon range
        scored = []
        for tid, tr in live_tracks.items():
            # Ground target (low alt, stationary) -> skip
            if tr.alt <= 100.0 and tr.vel <= 0:
                continue
            dist = haversine_m(RADAR_LAT, RADAR_LON, tr.lat, tr.lon)
            if dist > WEAPON_RANGE_M:
                continue
            threat = calc_threat(tr, RADAR_LAT, RADAR_LON)
            ttype = estimate_target_type(tr)
            scored.append((threat, tid, tr, dist, ttype))

        scored.sort(key=lambda x: -x[0])  # highest threat first

        # Step 3: print decision header + per-track info
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
                fires_for_this_target = [f.split(":")[1] for f in fires]
                if w.name not in self.used_weapons and w.name not in fires_for_this_target:
                    fires.append(f"FIRE:{w.name}:radar1:{tid}")
                    self.used_weapons.add(w.name)
                    self.fire_count += 1
                    # P2-2: record OODA latency (wall-clock from first detection to FIRE decision)
                    now = time.time()
                    latency = now - tr.first_seen
                    self.fire_latencies.append(latency)
                    print(f"    -> FIRE:{w.name}:{tid}")
                    break
            else:
                # No available weapon found for this target
                print(f"    -> no weapon for track {tid}")

        decision.fires = fires

        # Step 5: sensor mode
        if not live_tracks:
            decision.sensor_mode = "SEARCH"
            self.sensor_mode = "SEARCH"
        else:
            decision.sensor_mode = "TRACK"
            self.sensor_mode = "TRACK"

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

    def parse_evt_for_kills(self, final: bool = False):
        """Read .evt file, count new kills/misses and log weapon fired events.

        When final=True, re-reads all EVT content without skipping previously
        seen lines — ensures complete count on shutdown even if lines were
        only partially processed during the run.
        """
        if not Path(EVT_FILE).exists():
            return
        try:
            content = Path(EVT_FILE).read_text(encoding="utf-8")
        except OSError:
            return

        # Join continuation lines: strip any trailing backslash-newline combos
        # (handle both Unix \n and Windows \r\n line endings)
        content = re.sub(r'\\\r?\n', ' ', content)

        for line in content.split("\n"):
            if not line.strip():
                continue
            # When final=True, re-parse everything to get a complete count
            # (previously seen lines during the run are re-counted)
            if not final and line in self._seen_evt_lines:
                continue
            if "WEAPON_FIRED" in line:
                self._seen_evt_lines.add(line)
                print(f"  [WEAPON_FIRED] {line[:120]}")
            elif "Result: KILLED" in line:
                self.kill_count += 1
                print(f"  [KILLED] {line[:120]}")
                # Also parse the INTENDED_TARGET to find which track was killed.
                # After joining continuation lines, the full WEAPON_HIT record
                # is on ONE line (e.g. "WEAPON_HIT radar1 asm1 ... Result: KILLED").
                # Extract target name from "WEAPON_HIT radar1 asm1 ..." -> "asm1".
                hit_match = re.search(r'WEAPON_HIT\s+\S+\s+(\S+)', line)
                if hit_match:
                    target_name = hit_match.group(1)
                    for tid, tr in self.tracks.items():
                        if target_name in (f"asm{tid}", f"fighter{tid}", f"uav{tid}"):
                            tr.killed = True
                            print(f"  [KILL_FEEDBACK] track {tid} ({target_name}) marked killed via EVT")
            elif "WEAPON_MISSED" in line:
                self._seen_evt_lines.add(line)
                self.miss_count += 1
                print(f"  [MISSED] {line[:120]}")

    def poll_kill_assessment(self):
        """Read kill_assessment_result.txt written by AFSIM KILL_ASSESSMENT processor.
        Updates Track.killed flag so the decide() loop skips destroyed targets.
        """
        if not KILL_RESULT_FILE.exists():
            return
        try:
            content = KILL_RESULT_FILE.read_text(encoding="utf-8").strip()
        except OSError:
            return
        if not content:
            return

        # Format: "KILL:HIT:aim120_sim_1:asm1:2" or "KILL:KILLED:..."
        parts = content.split(":")
        if len(parts) < 5 or parts[0] != "KILL":
            return

        result_str = parts[1]  # HIT, KILLED, MISS, COAST_EXCEEDED, FUEL_EXHAUSTED
        weapon_name = parts[2]
        target_name = parts[3]  # e.g. "asm1", "fighter1"
        try:
            target_id = int(parts[4])
        except ValueError:
            target_id = -1

        if result_str in ("HIT", "KILLED"):
            # Mark track as killed so decide() excludes it from future allocation
            if target_id in self.tracks:
                self.tracks[target_id].killed = True
                print(f"  [KILL_ASM] {result_str} confirmed: track {target_id} ({target_name}) by {weapon_name}")
                self.kill_count += 1
            elif result_str == "KILLED":
                # Even without a track ID, log if target name is known
                print(f"  [KILL_ASM] {result_str} confirmed: {target_name} by {weapon_name}")
        elif result_str in ("MISS", "COAST_EXCEEDED", "FUEL_EXHAUSTED"):
            print(f"  [KILL_ASM] {result_str}: target {target_name} by {weapon_name}")
            self.miss_count += 1

        # Clear the file after consuming
        try:
            KILL_RESULT_FILE.unlink()
        except OSError:
            pass

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

    def wait_for_ack(self, timeout: float = 30.0) -> tuple:
        """Wait for ACK file, parse per-FIRE results.
        Returns (bool, list) — (received, fire_results).
        fire_results: list of "OK:weapon:track:num" or "FAIL:..." entries.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.afsim and self.afsim.poll() is not None:
                return (False, [])
            # Keep polling tracks while waiting for ACK — prevents OODA stall
            self.poll()
            try:
                if ACK_FILE.exists():
                    lines = ACK_FILE.read_text(encoding="utf-8").strip().splitlines()
                    if not lines:
                        time.sleep(0.05)
                        continue
                    first = lines[0].strip()
                    if first == "ACK":
                        ACK_FILE.unlink()
                        # Lines after ACK are per-fire results
                        results = [l.strip() for l in lines[1:] if l.strip()]
                        return (True, results)
            except OSError:
                pass
            time.sleep(0.05)
        return (False, [])

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self, external_afsim=None):
        print(f"[KC] Starting: {self.scenario_path}")
        print(f"[KC] Output EVT: {EVT_FILE}")

        # Clean slate
        for f in [CMD_FILE, SENSOR_FILE, ACK_FILE, KILL_RESULT_FILE]:
            if f.exists():
                try:
                    f.unlink()
                except:
                    pass

        import subprocess
        if external_afsim is not None:
            # Use externally-provided AFSIM process (already running)
            self.afsim = external_afsim
        else:
            # Run from WORKSPACE with relative scenario path.
            # Note: the scenario file itself contains "realtime" so no -rt flag needed.
            scenario_abs = Path(self.scenario_path).resolve()
            workspace_abs = WORKSPACE.resolve()
            scenario_name = scenario_abs.relative_to(workspace_abs)
            self.afsim = subprocess.Popen(
                [AFSIM_BIN, str(scenario_name)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(workspace_abs)
            )

        self.start_time = time.time()
        evt_check_interval = 1.0
        last_evt_check = 0.0

        try:
            while True:
                self.poll()

                now = time.time()
                if now - last_evt_check > evt_check_interval:
                    self.parse_evt_for_kills()
                    self.poll_kill_assessment()
                    last_evt_check = now

                if self.afsim.poll() is not None:
                    self.poll()
                    print(f"\n[KC] AFSIM exited: {self.afsim.returncode}")
                    break

                # Non-blocking read of any AFSIM stderr output
                try:
                    import os
                    fd = self.afsim.stderr.fileno()
                    os.set_blocking(fd, False)
                    while True:
                        try:
                            line = self.afsim.stderr.readline()
                            if not line:
                                break
                            line = line.decode("utf-8", errors="replace").strip()
                            if line and "KCMD:" in line:
                                print(f"  [KCMD] {line[:120]}")
                        except OSError:
                            break
                except (OSError, AttributeError):
                    pass

                # Make a decision
                decision = self.decide()

                if decision.fires:
                    # Batch write ALL fire commands at once
                    self.write_cmd(decision.fires)
                    for f in decision.fires:
                        print(f"  [FIRE] {f}")
                    self.write_sensor(decision.sensor_mode)

                    # Wait for ACK with retry on timeout (non-blocking poll)
                    ack_ok = False
                    fire_results = []
                    retries = 0
                    while retries <= 2:
                        ack_ok, fire_results = self.wait_for_ack(timeout=1.0)
                        if ack_ok:
                            break
                        retries += 1
                        if retries > 2:
                            break
                        print(f"  [ACK] Timeout, retrying ({retries}/2)...")
                        # Re-write fires + sensor to trigger AFSIM to re-process
                        self.write_cmd(decision.fires)
                        self.write_sensor(decision.sensor_mode)
                    if not ack_ok:
                        print(f"  [ACK] No ACK after 3 attempts, continuing...")
                    else:
                        # Process fire results: OK entries mean weapon was actually fired
                        # FAIL entries mean it wasn't — free that weapon slot for re-assignment
                        confirmed_fired = set()
                        for res in fire_results:
                            if res.startswith("OK:"):
                                items = res.split(":")
                                if len(items) >= 2:
                                    wname = items[1]
                                    confirmed_fired.add(wname)
                                    print(f"  [CONFIRMED] weapon {wname} fired OK")
                                    self.used_weapons.add(wname)
                            elif res.startswith("FAIL:"):
                                # Weapon failed to fire — remove from used_weapons so it can be re-assigned
                                items = res.split(":")
                                if len(items) >= 2:
                                    wname = items[1]
                                    if wname in self.used_weapons:
                                        self.used_weapons.discard(wname)
                                        print(f"  [RETRY] weapon {wname} failed, will retry next frame")
                        if not confirmed_fired:
                            print(f"  [ACK] No weapons confirmed fired, may retry next frame")
                else:
                    self.write_sensor(decision.sensor_mode)
                    time.sleep(0.02)

        except KeyboardInterrupt:
            print("\n[KC] Interrupted")
        finally:
            # ----------------------------------------------------------------
            # AFSIM has exited — write ACK, drain remaining stderr, then finalize
            # ----------------------------------------------------------------
            try:
                ACK_FILE.write_text("ACK", encoding="utf-8")
            except OSError:
                pass

            # Drain all remaining stderr now that AFSIM has exited
            try:
                _, stderr_remaining = self.afsim.communicate(timeout=2)
                if stderr_remaining:
                    for line in stderr_remaining.decode("utf-8", errors="replace").splitlines():
                        line = line.strip()
                        if line and "KCMD:" in line:
                            print(f"  [KCMD] {line[:120]}")
            except subprocess.TimeoutExpired:
                self.afsim.kill()

            # Give a moment, then final EVT parse
            time.sleep(0.3)
            self.poll()
            self.parse_evt_for_kills(final=True)
            self.print_summary()

    def print_summary(self):
        total_tracks = len(self.tracks)
        fired_count = self.fire_count
        killed_count = self.kill_count
        missed_count = self.miss_count
        # Tracks that were neither killed nor missed = leaked
        leak_count = total_tracks - killed_count - missed_count

        dt = self.decision_times
        avg_ms = (sum(dt) / len(dt) * 1000) if dt else 0
        max_ms = (max(dt) * 1000) if dt else 0
        min_ms = (min(dt) * 1000) if dt else 0

        lat = self.fire_latencies
        ooda_min = (min(lat) * 1000) if lat else 0
        ooda_max = (max(lat) * 1000) if lat else 0
        ooda_avg = (sum(lat) / len(lat) * 1000) if lat else 0

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
        print(f"  OODA延迟: min={ooda_min:.0f}ms max={ooda_max:.0f}ms avg={ooda_avg:.0f}ms")
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

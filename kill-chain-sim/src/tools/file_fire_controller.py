"""
Plan B E2E Runner — AFSIM writes track data to file, Python polls it.
Python writes FIRE commands to file, AFSIM reads them via KILL_CHAIN_CMD_READER.

AFSIM: kill_chain_np.txt (radar1 + aim120_sim + BLUE_TARGET)
Python: polls afsim_track_out.txt, writes FIRE commands to kill_chain_np_cmd.txt

Usage:
    python src/tools/file_fire_controller.py --scenario kill_chain_np.txt
"""

import argparse
import sys
import time
import re
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.shared_mem.shm_client import ShmClient


AFSIM_BIN = "D:/afsim-2.9.0-win64/bin/mission.exe"
TRACK_FILE = Path("C:/Users/15041/.openclaw/workspace/kill-chain-sim/afsim_track_out.txt")
CMD_FILE = Path("C:/Users/15041/.openclaw/workspace/kill-chain-sim/kill_chain_np_cmd.txt")
SCENARIO = "C:/Users/15041/.openclaw/workspace/kill-chain-sim/src/sim/kill_chain_np.txt"

# Regex: matches "TRACK: id=X lat=Y lon=Z alt=A vel=S hdg=H"
TRACK_RE = re.compile(
    r"TRACK:\s*id=(\d+)\s+lat=([-\d.]+)\s+lon=([-\d.]+)\s+alt=([-\d.]+)\s+vel=([-\d.]+)\s+hdg=([-\d.]+)"
)

MIN_ALT_FIRE = 15000.0  # meters — fire only at targets below this altitude


class PlanBE2E:
    def __init__(self, scenario_path: str):
        self.scenario_path = scenario_path
        self.afsim = None
        self.fired_tracks = set()
        self.last_cmd = ""
        self.last_file_mtime = 0
        self.last_file_size = 0
        self.tracks = {}      # track_id -> {lat, lon, alt, vel, hdg}
        self.last_track_file_content = ""  # track last-seen content to detect changes

    def write_fire(self, weapon: str, track_name: str, track_num: int):
        cmd = f"FIRE:{weapon}:{track_name}:{track_num}"
        if cmd == self.last_cmd:
            return
        try:
            CMD_FILE.write_text(cmd + "\n", encoding="utf-8")
            self.last_cmd = cmd
            print(f"  [E2E] FIRE -> {cmd}")
        except Exception as e:
            print(f"  [E2E] Write FIRE error: {e}")

    def parse_and_fire(self, content: str):
        """Parse TRACK lines from full file content."""
        lines = content.strip().split("\n")

        for line in lines:
            line = line.strip()
            if line.startswith("AFSIM_MS:"):
                try:
                    afsim_sim_ms = int(line.split(":")[1].strip())
                    t_now = time.time() * 1000
                    latency_ms = t_now - afsim_sim_ms
                    print(f"  [E2E] AFSIM→Python latency: {latency_ms:.1f}ms  (AFSIM_sim_ms={afsim_sim_ms})")
                except (IndexError, ValueError):
                    pass
                continue
        for line in lines:
            line = line.strip()
            if not line.startswith("TRACK:"):
                continue
            m = TRACK_RE.search(line)
            if not m:
                continue
            try:
                track_id = int(m.group(1))
                lat      = float(m.group(2))
                lon      = float(m.group(3))
                alt      = float(m.group(4))
                vel      = float(m.group(5))
                hdg      = float(m.group(6))
            except ValueError:
                continue

            self.tracks[track_id] = {"lat": lat, "lon": lon, "alt": alt, "vel": vel, "hdg": hdg}

            if track_id in self.fired_tracks:
                continue

            # Fire at targets below altitude threshold
            if alt < MIN_ALT_FIRE:
                self.write_fire("aim120_sim", "radar1", track_id)
                self.fired_tracks.add(track_id)
                print(f"  [E2E] Track {track_id}: lat={lat:.4f} lon={lon:.4f} alt={alt:.0f}m -> queued")

    def poll_track_file(self):
        """Poll track file for changes."""
        if not TRACK_FILE.exists():
            return

        try:
            mtime = TRACK_FILE.stat().st_mtime
            size = TRACK_FILE.stat().st_size
        except OSError:
            return

        if mtime != self.last_file_mtime or size != self.last_file_size:
            try:
                content = TRACK_FILE.read_text(encoding="utf-8")
            except OSError:
                return
            if content != self.last_track_file_content:
                t_now = time.time()
                file_age_ms = (t_now - mtime) * 1000
                print(f"  [E2E] File latency: {file_age_ms:.1f}ms  (file mtime={mtime:.3f} python_now={t_now:.3f})")
                self.last_track_file_content = content
                self.last_file_mtime = mtime
                self.last_file_size = size
                self.parse_and_fire(content)

    def run(self):
        print(f"[E2E] Starting AFSIM: {self.scenario_path}")
        print(f"[E2E] Polling track file: {TRACK_FILE}")
        print(f"[E2E] Writing FIRE commands to: {CMD_FILE}")

        # Clear stale command file
        if CMD_FILE.exists():
            CMD_FILE.unlink()

        import subprocess
        self.afsim = subprocess.Popen(
            [AFSIM_BIN, "-rt", self.scenario_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(Path(self.scenario_path).resolve().parent)
        )

        try:
            while True:
                # Poll track file every 50ms
                self.poll_track_file()
                time.sleep(0.05)

                # Check if AFSIM has exited
                if self.afsim.poll() is not None:
                    # Drain any remaining track data
                    self.poll_track_file()
                    print(f"[E2E] AFSIM stopped with code {self.afsim.returncode}")
                    break
        except KeyboardInterrupt:
            print("\n[E2E] Interrupted")
        finally:
            if self.afsim and self.afsim.poll() is None:
                self.afsim.terminate()
                try:
                    self.afsim.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.afsim.kill()
            print(f"[E2E] Done")


def main():
    parser = argparse.ArgumentParser(description="Plan B E2E Runner")
    parser.add_argument("--scenario", default=SCENARIO)
    args = parser.parse_args()

    e2e = PlanBE2E(args.scenario)
    e2e.run()


if __name__ == "__main__":
    main()

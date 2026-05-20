#!/usr/bin/env python
"""
AFSIM to Shared Memory Bridge
=============================

Runs AFSIM as a subprocess, captures TRACK: lines from stdout,
and writes them to shared memory for the kill chain manager.

Usage:
    python afsim_bridge.py --scenario kill_chain_minimal.txt --shm kill_chain_shm
"""

import argparse
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from src.core.shared_mem.shm_client import (
    ShmClient, TrackEntry, TRACKS_OFFSET, TRACK_SIZE
)


TRACK_PATTERN = re.compile(
    r"TRACK:\s*id=(\d+)\s+lat=([-\d.]+)\s+lon=([-\d.]+)\s+alt=([-\d.]+)\s+vel=([-\d.]+)\s+hdg=([-\d.]+)"
)


class AfsimBridge:
    def __init__(self, scenario_path: str, shm_name: str = "kill_chain_shm",
                 afsim_bin: str = None, work_dir: str = None):
        self.scenario_path = scenario_path
        self.shm_name = shm_name
        self.afsim_bin = afsim_bin or "D:/afsim-2.9.0-win64/bin/mission.exe"
        # Resolve scenario to absolute path once —传给 mission.exe 的是绝对路径，不受 cwd 影响
        self.scenario_path = str(Path(scenario_path).resolve())
        self.work_dir = work_dir or str(Path(scenario_path).resolve().parent)
        
        self.shm_client = ShmClient(shm_name)
        self.proc = None
        self.track_count = 0
        self.running = False

    def connect_shm(self) -> bool:
        try:
            return self.shm_client.connect()
        except Exception as e:
            print(f"[Bridge] SHM connect failed: {e}")
            return False

    def write_track(self, track_id: int, lat: float, lon: float,
                    alt: float, vel: float, hdg: float):
        """Write a track entry to shared memory."""
        track = TrackEntry()
        track.track_id = track_id
        track.lat = lat
        track.lon = lon
        track.altitude = alt
        track.velocity = vel
        track.heading = hdg
        track.timestamp_ms = time.time() * 1000
        track.type = 2  # UCAV
        track.force = 1  # hostile
        track.track_quality = 75
        track.padding = 0

        # Round-robin through 512 slots so consumers can detect stale data
        # by comparing their previous read cursor against header.track_count
        slot = self.track_count % 512
        offset = TRACKS_OFFSET + slot * TRACK_SIZE
        self.shm_client._write_track(offset, track)

        header = self.shm_client._read_header()
        header.track_count = self.track_count + 1   # consumers read this as "latest count"
        header.timestamp_ms = int(time.time() * 1000)
        self.shm_client._write_header(header)

        self.track_count += 1
        if self.track_count % 100 == 0:
            print(f"[Bridge] Tracks written: {self.track_count}")

    def run(self):
        """Run AFSIM and pump TRACK: lines to SHM."""
        cmd = [self.afsim_bin, "-rt", self.scenario_path]
        print(f"[Bridge] Starting: {' '.join(cmd)}")
        
        self.proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=self.work_dir
        )
        
        self.running = True
        line_count = 0
        
        try:
            for line in self.proc.stdout:
                line_count += 1
                
                # Parse and write to SHM
                m = TRACK_PATTERN.search(line)
                if m:
                    track_id = int(m.group(1))
                    lat = float(m.group(2))
                    lon = float(m.group(3))
                    alt = float(m.group(4))
                    vel = float(m.group(5))
                    hdg = float(m.group(6))
                    self.write_track(track_id, lat, lon, alt, vel, hdg)
                    
            self.proc.wait()
            self.running = False
            print(f"[Bridge] AFSIM exited with code {self.proc.returncode}, processed {line_count} lines, {self.track_count} tracks")
            
        except KeyboardInterrupt:
            print("[Bridge] Interrupted")
            self.stop()

    def stop(self):
        self.running = False
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.shm_client.close()


def main():
    parser = argparse.ArgumentParser(description="AFSIM to SHM Bridge")
    parser.add_argument("--scenario", required=True,
                       help="Path to AFSIM scenario .txt file")
    parser.add_argument("--shm", default="kill_chain_shm",
                       help="Shared memory name (default: kill_chain_shm)")
    parser.add_argument("--afsim-bin",
                       default="D:/afsim-2.9.0-win64/bin/mission.exe",
                       help="AFSIM mission.exe path")
    args = parser.parse_args()

    bridge = AfsimBridge(args.scenario, args.shm, args.afsim_bin)
    
    if not bridge.connect_shm():
        print("[Bridge] Failed to connect to shared memory")
        sys.exit(1)
    
    print(f"[Bridge] Connected to SHM: {args.shm}")
    
    def signal_handler(sig, frame):
        print("\n[Bridge] Shutting down...")
        bridge.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGBREAK, signal_handler)  # Windows Ctrl+C
    
    bridge.run()


if __name__ == "__main__":
    main()

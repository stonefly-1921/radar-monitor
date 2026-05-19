"""
AFSIM Track File Monitor
=========================

Watches AFSIM's output log file for TRACK: lines written via `writeln`
and writes them into shared memory for the kill chain Python client.

Usage:
    python -m src.core.shared_mem.track_file_monitor --log <path> --shm <name>
"""

import argparse
import os
import re
import time
import sys
from pathlib import Path
from threading import Thread

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.shared_mem.shm_client import ShmClient, TrackEntry, SensorEntry


# Regex to parse TRACK: id=X lat=X lon=X alt=X vel=X hdg=X
TRACK_PATTERN = re.compile(
    r"TRACK:\s*id=(\d+)\s+lat=([-\d.]+)\s+lon=([-\d.]+)\s+alt=([-\d.]+)\s+vel=([-\d.]+)\s+hdg=([-\d.]+)"
)


class TrackFileMonitor:
    """Monitor AFSIM log file for TRACK: lines and write to shared memory."""

    def __init__(self, log_path: str, shm_name: str = "kill_chain_shm"):
        self.log_path = Path(log_path)
        self.shm_client = ShmClient(shm_name)
        self.running = False
        self.track_count = 0

    def connect(self) -> bool:
        return self.shm_client.connect()

    def start(self, poll_interval: float = 0.5):
        """Start monitoring in background thread."""
        self.running = True
        self.thread = Thread(target=self._run, args=(poll_interval,), daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=2)
        self.shm_client.close()

    def _run(self, poll_interval: float):
        file_pos = 0
        if self.log_path.exists():
            file_pos = self.log_path.stat().st_size

        while self.running:
            if not self.log_path.exists():
                time.sleep(poll_interval)
                continue

            current_size = self.log_path.stat().st_size
            if current_size < file_pos:
                # File was truncated/rotated
                file_pos = 0
                self.shm_client.shm_client.connect()  # Re-init header

            if current_size > file_pos:
                with open(self.log_path, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(file_pos)
                    new_lines = f.readlines()
                    file_pos = f.tell()

                for line in new_lines:
                    self._process_line(line)

            time.sleep(poll_interval)

    def _process_line(self, line: str):
        m = TRACK_PATTERN.search(line)
        if not m:
            return

        try:
            track_id = int(m.group(1))
            lat = float(m.group(2))
            lon = float(m.group(3))
            alt = float(m.group(4))
            vel = float(m.group(5))
            hdg = float(m.group(6))

            # Write to shared memory track slot
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

            # Write to next slot (round-robin)
            slot = self.track_count % 512
            offset = 128 + slot * 72  # TRACKS_OFFSET
            self.shm_client._write_track(offset, track)

            # Update header
            header = self.shm_client._read_header()
            header.track_count = min(self.track_count + 1, 512)
            header.timestamp_ms = int(time.time() * 1000)
            self.shm_client._write_header(header)

            self.track_count += 1
            print(f"  [TrackFileMonitor] Track {track_id}: lat={lat:.4f} lon={lon:.4f} alt={alt:.0f}m vel={vel:.0f}m/s")

        except Exception as e:
            print(f"  [TrackFileMonitor] Parse error: {e} on line: {line.strip()}")


def main():
    parser = argparse.ArgumentParser(description="Monitor AFSIM log for track data")
    parser.add_argument("--log", default="C:/Users/15041/.openclaw/workspace/kill-chain-sim/output/kill_chain.log",
                        help="AFSIM log file path")
    parser.add_argument("--shm", default="kill_chain_shm",
                        help="Shared memory name")
    parser.add_argument("--poll", type=float, default=0.5,
                        help="Poll interval in seconds")
    args = parser.parse_args()

    monitor = TrackFileMonitor(args.log, args.shm)
    if not monitor.connect():
        print(f"Failed to connect to shared memory: {args.shm}")
        sys.exit(1)

    print(f"Monitoring {args.log} -> {args.shm}")
    monitor.start(poll_interval=args.poll)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        monitor.stop()


if __name__ == "__main__":
    main()
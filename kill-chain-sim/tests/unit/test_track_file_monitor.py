"""Unit tests for TrackFileMonitor."""
import os
import sys
import time
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.shared_mem.track_file_monitor import TrackFileMonitor, TRACK_PATTERN
from src.core.shared_mem.shm_client import ShmClient, TRACKS_OFFSET, TRACK_SIZE


def test_track_regex():
    """Test that the TRACK regex parses correctly."""
    line = "TRACK: id=42 lat=38.1234 lon=-117.5678 alt=10000.5 vel=250.3 hdg=90.0"
    m = TRACK_PATTERN.search(line)
    assert m is not None, "Regex should match"
    assert m.group(1) == "42"
    assert abs(float(m.group(2)) - 38.1234) < 0.001
    assert abs(float(m.group(3)) - (-117.5678)) < 0.001
    assert abs(float(m.group(4)) - 10000.5) < 0.001
    assert abs(float(m.group(5)) - 250.3) < 0.001
    assert abs(float(m.group(6)) - 90.0) < 0.001
    print("PASS: test_track_regex")


def test_track_file_monitor():
    """Test TrackFileMonitor writes tracks to shared memory."""
    # Create a temp log file
    fd, tmp = tempfile.mkstemp(suffix=".log")
    os.close(fd)

    try:
        monitor = TrackFileMonitor(tmp, "test_track_monitor_shm")
        assert monitor.connect()
        monitor.start(poll_interval=0.1)

        # Write some fake TRACK lines
        with open(tmp, "w") as f:
            f.write("TRACK: id=1 lat=38.5 lon=-117.3 alt=10000 vel=200 hdg=90\n")
            f.write("TRACK: id=2 lat=38.6 lon=-117.4 alt=11000 vel=210 hdg=95\n")

        time.sleep(1.0)  # Let monitor pick up the lines

        monitor.stop()

        # Check shared memory
        client = ShmClient("test_track_monitor_shm")
        assert client.connect()
        tracks = client.get_tracks()

        # At least one track should be captured
        assert len(tracks) >= 1, f"Expected >= 1 tracks, got {len(tracks)}"
        print(f"  Captured {len(tracks)} track(s) from file monitor")
        for t in tracks:
            print(f"    Track {t.track_id}: lat={t.lat:.4f} lon={t.lon:.4f}")

        client.close()
        print("PASS: test_track_file_monitor")

    finally:
        os.unlink(tmp)


if __name__ == "__main__":
    test_track_regex()
    test_track_file_monitor()
    print()
    print("All track file monitor tests passed!")
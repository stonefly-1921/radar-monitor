"""Unit tests for ShmClient."""
import os
import sys
import time
import mmap
import tempfile
from pathlib import Path

# Ensure project root in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.shared_mem.shm_client import (
    ShmClient, TrackEntry, SensorEntry, WeaponEntry, CmdEntry,
    SensorMode, WeaponStatus, CmdType, TargetType,
    MAGIC, FENCE_VALUE, MAX_TRACKS, MAX_CMDS,
    TRACKS_OFFSET, CMDS_OFFSET, TRACK_SIZE, CMD_SIZE, HEADER_SIZE
)


def test_shm_creation():
    """Test that we can create and connect to shared memory."""
    client = ShmClient("test_kill_chain_shm")
    assert client.connect(), "Failed to connect to shared memory"
    assert client.is_valid(), "Invalid magic after connect"
    header = client._read_header()
    assert header.magic == MAGIC
    client.close()
    print("PASS: test_shm_creation")


def test_track_roundtrip():
    """Test writing and reading back a TrackEntry."""
    client = ShmClient("test_kill_chain_shm")
    assert client.connect()

    # Write a track
    track = TrackEntry()
    track.track_id = 42
    track.lat = 38.5
    track.lon = -117.3
    track.altitude = 10000.0
    track.velocity = 250.0
    track.heading = 90.0
    track.timestamp_ms = 1234567890.0
    track.type = TargetType.UCAV
    track.force = 1  # hostile
    track.track_quality = 85
    track.padding = 0

    # Write to slot 0
    client._write_track(TRACKS_OFFSET + 0 * TRACK_SIZE, track)

    # Update header to say 1 track
    header = client._read_header()
    header.track_count = 1
    client._write_header(header)

    # Read back
    tracks = client.get_tracks()
    assert len(tracks) == 1
    t = tracks[0]
    assert t.track_id == 42
    assert abs(t.lat - 38.5) < 0.001
    assert abs(t.lon - (-117.3)) < 0.001
    assert abs(t.altitude - 10000.0) < 1.0
    assert t.type == TargetType.UCAV
    assert t.force == 1
    assert t.track_quality == 85

    client.close()
    print("PASS: test_track_roundtrip")


def test_command_queue():
    """Test sending a command and getting acknowledgment."""
    client = ShmClient("test_kill_chain_shm")
    assert client.connect()

    # Queue a sensor control command
    sensor_id = 100
    mode = SensorMode.TRACK
    result = client.send_sensor_control(sensor_id, mode)
    assert result, "send_sensor_control returned False"

    # Read the queued command
    header = client._read_header()
    assert header.cmd_in == 1
    idx = (header.cmd_in - 1) % MAX_CMDS
    cmd = client._read_cmd(CMDS_OFFSET + idx * CMD_SIZE)

    assert cmd.cmd_id == 1
    assert cmd.type == CmdType.SENSOR_CONTROL
    assert cmd.param1 == sensor_id
    assert cmd.param2 == int(mode)
    assert cmd.acknowledged == 0

    # Acknowledge it (simulate AFSIM response)
    cmd.acknowledged = 1
    client._write_cmd(CMDS_OFFSET + idx * CMD_SIZE, cmd)

    # Poll for ack
    ack = client.poll_command_ack(1, timeout_ms=500)
    assert ack, "poll_command_ack timed out"

    client.close()
    print("PASS: test_command_queue")


def test_multiple_tracks():
    """Test writing multiple tracks."""
    client = ShmClient("test_kill_chain_shm")
    assert client.connect()

    header = client._read_header()
    header.track_count = 3
    client._write_header(header)

    for i in range(3):
        track = TrackEntry()
        track.track_id = i + 1
        track.lat = 38.0 + i * 0.1
        track.lon = -117.0 - i * 0.1
        track.altitude = 5000.0 + i * 1000
        track.velocity = 200.0 + i * 10
        track.heading = float(i * 30)
        track.timestamp_ms = time.time() * 1000
        track.type = TargetType.AIRCRAFT
        track.force = 2
        track.track_quality = 70 + i
        client._write_track(TRACKS_OFFSET + i * TRACK_SIZE, track)

    tracks = client.get_tracks()
    assert len(tracks) == 3
    assert tracks[0].track_id == 1
    assert tracks[1].track_id == 2
    assert tracks[2].track_id == 3

    client.close()
    print("PASS: test_multiple_tracks")


def test_weapon_assign_command():
    """Test WEAPON_ASSIGN command."""
    client = ShmClient("test_kill_chain_shm")
    assert client.connect()

    result = client.send_weapon_assign(weapon_id=5, track_id=100, priority=0.95)
    assert result

    header = client._read_header()
    idx = (header.cmd_in - 1) % MAX_CMDS
    cmd = client._read_cmd(CMDS_OFFSET + idx * CMD_SIZE)

    assert cmd.type == CmdType.WEAPON_ASSIGN
    assert cmd.param1 == 5  # weapon_id
    assert cmd.target_id == 100  # track_id
    assert abs(cmd.param3 - 0.95) < 0.001

    client.close()
    print("PASS: test_weapon_assign_command")


if __name__ == "__main__":
    test_shm_creation()
    test_track_roundtrip()
    test_command_queue()
    test_multiple_tracks()
    test_weapon_assign_command()
    print()
    print("All tests passed!")
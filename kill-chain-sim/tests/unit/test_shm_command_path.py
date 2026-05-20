"""Unit tests for the Python->AFSIM command path (send_weapon_assign + poll_command_ack)."""
import os
import sys
import time
import tempfile
import pytest
from pathlib import Path

# Ensure project root in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.shared_mem.shm_client import (
    ShmClient, TrackEntry, CmdEntry,
    CmdType, TargetType,
    MAGIC, MAX_CMDS, CMDS_OFFSET, CMDACK_OFFSET, CMD_SIZE, HEADER_SIZE
)


@pytest.fixture
def fresh_shm_client():
    """Provide a ShmClient connected to a brand-new clean test shm file."""
    # Use a unique temp file so this test never conflicts with other tests
    fd, tmp_path = tempfile.mkstemp(suffix=".dat", prefix="test_cmd_path_")
    os.close(fd)

    client = ShmClient.__new__(ShmClient)
    client.shm_name = "test_cmd_path"
    client.shm_path = Path(tmp_path)
    client.fd = None
    client.mm = None
    client._next_cmd_id = 1

    if not client.connect():
        os.unlink(tmp_path)
        pytest.fail("Failed to connect to shared memory")

    yield client

    client.close()
    # Clean up temp file
    try:
        os.unlink(tmp_path)
    except Exception:
        pass


def test_weapon_assign_command_path(fresh_shm_client):
    """End-to-end: send_weapon_assign -> shared memory -> poll_command_ack.

    Verifies:
    1. reinitialize() resets cmd_in/cmd_out to 0 and clears the queue
    2. send_weapon_assign() writes a correctly-formatted WEAPON_ASSIGN command
    3. poll_command_ack() correctly waits for and detects an ack
    """
    client = fresh_shm_client

    # --- Step 1: reinitialize() gives us a clean slate ---
    result = client.reinitialize()
    assert result, "reinitialize() returned False"

    header = client._read_header()
    assert header.cmd_in == 0, f"cmd_in should be 0 after reinitialize, got {header.cmd_in}"
    assert header.cmd_out == 0, f"cmd_out should be 0 after reinitialize, got {header.cmd_out}"

    # --- Step 2: send_weapon_assign() queues a command ---
    weapon_id = 7
    track_id = 42
    priority = 0.85
    send_ok = client.send_weapon_assign(weapon_id=weapon_id, track_id=track_id, priority=priority)
    assert send_ok, "send_weapon_assign() returned False"

    # --- Step 3: verify command was written with correct values ---
    header = client._read_header()
    assert header.cmd_in == 1, f"cmd_in should be 1 after send, got {header.cmd_in}"

    idx = (header.cmd_in - 1) % MAX_CMDS
    cmd = client._read_cmd(CMDS_OFFSET + idx * CMD_SIZE)

    assert cmd.cmd_id == 1, f"cmd_id should be 1, got {cmd.cmd_id}"
    assert cmd.type == CmdType.WEAPON_ASSIGN, f"type should be WEAPON_ASSIGN ({CmdType.WEAPON_ASSIGN}), got {cmd.type}"
    assert cmd.param1 == weapon_id, f"param1 (weapon_id) should be {weapon_id}, got {cmd.param1}"
    assert cmd.target_id == track_id, f"target_id (track_id) should be {track_id}, got {cmd.target_id}"
    assert abs(cmd.param3 - priority) < 0.001, f"param3 (priority) should be ~{priority}, got {cmd.param3}"
    assert cmd.acknowledged == 0, f"acknowledged should be 0 (not yet ack'd), got {cmd.acknowledged}"

    # --- Step 4: simulate AFSIM writing the ack (AFSIM writes to CmdAck region) ---
    cmd.acknowledged = 1
    client._write_cmd(CMDACK_OFFSET + idx * CMD_SIZE, cmd)

    # --- Step 5: poll_command_ack() detects the ack ---
    ack_ok = client.poll_command_ack(cmd.cmd_id, timeout_ms=2000)
    assert ack_ok, "poll_command_ack() returned False after AFSIM wrote ack"

    print("PASS: test_weapon_assign_command_path")
#!/usr/bin/env python3
"""
Test: Write a command to SHM and verify the plugin detects it.
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.core.shared_mem.shm_client import ShmClient, CmdType

# Connect to SHM
client = ShmClient("kill_chain_shm")
if not client.connect():
    print("[TEST] Failed to connect to SHM")
    sys.exit(1)

print(f"[TEST] Connected to SHM")
header = client.read_header()
print(f"[TEST] Header: magic=0x{header.magic:08X} tracks={header.track_count} cmd_in={header.cmd_in}")

# Write a test command (type=SENSOR_CONTROL, target_id=999)
cmd_id = client.write_cmd(
    cmd_type=CmdType.SENSOR_CONTROL,
    sender_id=99,
    target_id=999,
    param1=1,  # sensor_id
    param2=3,  # mode = TRACK
)
print(f"[TEST] Wrote cmd_id={cmd_id}")

# Wait for plugin to process
time.sleep(1)

# Check cmd_out
header = client.read_header()
print(f"[TEST] After plugin check: cmd_in={header.cmd_in} cmd_out={header.cmd_out}")
if header.cmd_out > 0:
    print("[TEST] SUCCESS: Plugin detected command!")
else:
    print("[TEST] Plugin has not processed command yet")

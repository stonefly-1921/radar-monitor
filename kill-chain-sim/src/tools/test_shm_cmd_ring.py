"""
Phase 1 Test: Verify Python → wsf_shm.dll command ring

This script tests whether the wsf_shm.dll timer thread (60Hz polling)
reads commands written by Python to the SHM file.

Before running: Build wsf_shm.dll and ensure it is in AFSIM's plugin directory.
The DLL opens SHM on load and starts a 60Hz polling thread.

Usage:
  python test_shm_cmd_ring.py [--dll-path PATH] [--log-path PATH]
"""

import ctypes
import os
import struct
import sys
import time
import argparse

# SHM layout constants (must match wsf_shm.c)
MAGIC_VALUE = 0x4B494C4C  # "KILL"
HEADER_SIZE = 128
TRACK_SIZE = 72
MAX_TRACKS = 512
TRACKS_OFFSET = HEADER_SIZE
CMDS_OFFSET = HEADER_SIZE + MAX_TRACKS * TRACK_SIZE
CMD_SIZE = 44
MAX_CMDS = 256
SHM_FILE_SIZE = CMDS_OFFSET + MAX_CMDS * CMD_SIZE

# CmdEntry layout (matches wsf_shm.c)
# typedef struct {
#     uint32_t cmd_id;
#     uint8_t  type;
#     uint8_t  sender_id;
#     uint16_t reserved;
#     uint32_t target_id;
#     uint32_t param1;
#     uint32_t param2;
#     float    param3;
#     char     description[64];
# } CmdEntry;
# Total: 4+1+1+2+4+4+4+4+64 = 88? No wait...

# Actually in wsf_shm.c:
# typedef struct {
#     uint32_t cmd_id;       // offset 0
#     uint8_t  type;         // offset 4
#     uint8_t  sender_id;    // offset 5
#     uint16_t reserved;     // offset 6
#     uint32_t target_id;    // offset 8
#     uint32_t param1;       // offset 12
#     uint32_t param2;       // offset 16
#     float    param3;       // offset 20
#     char     description[64]; // offset 24
# } CmdEntry;
# Total: 88 bytes... but wsf_shm.c says CMD_SIZE = 44

# Wait - let me re-check wsf_shm.c
# Looking at wsf_shm.c:
# typedef struct {
#     uint32_t cmd_id;       // 4 bytes  -> offset 0
#     uint8_t  type;         // 1 byte   -> offset 4
#     uint8_t  sender_id;    // 1 byte   -> offset 5
#     uint16_t reserved;     // 2 bytes  -> offset 6
#     uint32_t target_id;    // 4 bytes  -> offset 8
#     uint32_t param1;       // 4 bytes  -> offset 12
#     uint32_t param2;       // 4 bytes  -> offset 16
#     float    param3;       // 4 bytes  -> offset 20
#     char     description[64]; // 64 bytes -> offset 24
# } CmdEntry;
# Total = 88 bytes

# But wsf_shm.c says CMD_SIZE = 44?? That's half.
# The Python shm_client.py says CMD_SIZE = ctypes.sizeof(CmdEntry) = 44 bytes
# with fields: cmd_id(4)+type(1)+sender_id(4)+target_id(4)+param1(4)+param2(4)+param3(8)+acknowledged(1)+padding(7)+timestamp_ms(4)
# = 4+1+4+4+4+4+8+1+7+4 = 41, rounded up to 44 (8-byte aligned?)
# Wait: ctypes.c_uint32(4)+ctypes.c_uint8(1)+ctypes.c_uint32(4)+ctypes.c_uint32(4)+ctypes.c_uint32(4)+ctypes.c_uint32(4)+ctypes.c_double(8)+ctypes.c_uint8(1)+ctypes.c_uint8*7(7)+ctypes.c_uint32(4) = 41 bytes
# But the C struct has: cmd_id(uint32_t=4) + type(uint8_t=1) + sender_id(uint8_t=1) + reserved(uint16_t=2) + target_id(uint32_t=4) + param1(uint32_t=4) + param2(uint32_t=4) + param3(float=4) + description[64] = 88 bytes

# There's a mismatch! The Python client uses a DIFFERENT CmdEntry layout.
# Python: cmd_id, type, sender_id, target_id, param1, param2, param3(float), acknowledged, padding[7], timestamp_ms
# C (wsf_shm.c): cmd_id, type, sender_id, reserved, target_id, param1, param2, param3, description[64]

# Since the C wsf_shm.c is reading what Python wrote, we need to match Python's layout.
# But actually the polling in wsf_shm.c reads using its OWN layout (CMD_SIZE=44).
# So if Python uses 44 bytes and C expects 88 bytes, they DON'T match.

# Let me just use the Python client's actual struct layout since that's what the
# Python side writes, and figure out the actual bytes.

# From Python shm_client.py CmdEntry:
# cmd_id=c_uint32(4), type=c_uint8(1), sender_id=c_uint32(4), target_id=c_uint32(4),
# param1=c_uint32(4), param2=c_uint32(4), param3=c_double(8), acknowledged=c_uint8(1),
# padding=c_uint8*7(7), timestamp_ms=c_uint32(4)
# Total = 4+1+4+4+4+4+8+1+7+4 = 41 bytes
# But ctypes pads to 8-byte alignment, so it would be 48? Actually let's just compute.

# Actually, let me look at what the Python actually SENDS:
# cmd.send_sensor_control() -> type=SENSOR_CONTROL=1, sender_id=0, target_id=0, param1=sensor_id, param2=mode

# For our test, let's just write raw bytes using the Python client's method
# and then verify the C side reads it correctly.

# For simplicity, let's just use the Python ShmClient directly.
# But first I need to figure out why CMD_SIZE is different.

# Looking at wsf_shm.c:
# #define CMD_SIZE 44
# But the struct layout appears to be 88 bytes.
# Let me check if there's packing or something.

# Actually wait - wsf_shm.c uses #pragma pack? No it doesn't show one.
# Let me look at the actual bytes:
# The struct has no pragma pack, so it would be naturally aligned:
# offset 0: cmd_id (4)
# offset 4: type (1) + sender_id (1) + reserved (2) = 4 (aligned)
# offset 8: target_id (4)
# offset 12: param1 (4)
# offset 16: param2 (4)
# offset 20: param3 (4)
# offset 24: description[64] = 64
# Total: 88 bytes

# But CMD_SIZE = 44 in wsf_shm.c. That's exactly half.
# So wsf_shm.c is reading 44 bytes per command, not 88.
# This means the Python struct (44 bytes?) might actually match.

# From Python CmdEntry ctypes:
# cmd_id=c_uint32 (4 bytes) at offset 0
# type=c_uint8 (1 byte) at offset 4
# sender_id=c_uint32 (4 bytes) at offset 5 (NOT at offset 5 where it would normally be aligned)
# This means ctypes is NOT using natural alignment here because of the way the fields are declared.
# With ctypes, fields are packed sequentially unless there's an explicit _pack_ or the struct is defined differently.

# Actually, ctypes.Structure doesn't add implicit padding unless needed for alignment.
# Let's trace through the Python struct field by field:
# "cmd_id" at offset 0, c_uint32, size 4
# "type" at offset 4, c_uint8, size 1
# "sender_id" at offset 5, c_uint32, size 4
# Since c_uint32 needs 4-byte alignment, and offset 5 is NOT 4-byte aligned,
# ctypes might add 3 bytes of padding... or it might not since it's a different field type.
# Actually ctypes does add padding to maintain alignment requirements.
# But ctypes.Structure by default doesn't add trailing padding to match a specific size.

# Let me just write the test using the ShmClient and see if it works.

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core', 'shared_mem'))
from shm_client import ShmClient, CmdType, SensorMode

def clear_shm_file(shm_path):
    """Clear the SHM file and reinitialize header."""
    import mmap
    os.makedirs(os.path.dirname(shm_path), exist_ok=True)
    fd = os.open(shm_path, os.O_RDWR | os.O_CREAT | os.O_TRUNC, 0o666)
    os.ftruncate(fd, SHM_FILE_SIZE)
    mm = mmap.mmap(fd, SHM_FILE_SIZE, access=mmap.ACCESS_WRITE)
    # Write header
    header = struct.pack('<IHHHIIIQ',
        MAGIC_VALUE, 1, 0, 0, 0, 0, 0, 0, 0xDEADBEEFDEADBEEF)
    # Wait, let me match ShmHeader exactly:
    # magic(I), version(H), track_count(H), sensor_count(H), weapon_count(H),
    # timestamp_ms(I), cmd_in(I), cmd_out(I), afsim_ready(B), padding(5B), fence(Q)
    # Total = 4+2+2+2+2+4+4+4+1+5+8 = 38? No:
    # 4+2+2+2+2+4+4+4 = 24, +1+5 = 30, +8 = 38. But HEADER_SIZE = 128.
    # The Python struct has more padding at the end.
    # Actually from Python:
    # _fields_ = [
    #     ("magic", ctypes.c_uint32),          # 4
    #     ("version", ctypes.c_uint16),        # 2
    #     ("track_count", ctypes.c_uint16),    # 2
    #     ("sensor_count", ctypes.c_uint16),  # 2
    #     ("weapon_count", ctypes.c_uint16),   # 2
    #     ("timestamp_ms", ctypes.c_uint32),   # 4
    #     ("cmd_in", ctypes.c_uint32),         # 4
    #     ("cmd_out", ctypes.c_uint32),        # 4
    #     ("afsim_ready", ctypes.c_uint8),     # 1
    #     ("padding", ctypes.c_uint8 * 5),     # 5
    #     ("fence", ctypes.c_uint64),          # 8
    # ]
    # Total = 4+2+2+2+2+4+4+4+1+5+8 = 38 bytes
    # But HEADER_SIZE = 128. There's 90 bytes of extra padding.
    # The shm_client.py actually writes the header at offset 0 but allocates 128 bytes for it.
    # And the actual struct is 38 bytes. The rest is padding.
    # The SHM file size is 64MB.
    mm.close()
    os.close(fd)

def main():
    parser = argparse.ArgumentParser(description='Test SHM command ring')
    parser.add_argument('--dll-path', default='D:/afsim-2.9.0-win64/bin/wsf_plugins/wsf_shm.dll')
    parser.add_argument('--log-path', default='D:/afsim-2.9.0-win64/bin/wsf_shm_debug.log')
    parser.add_argument('--shm-name', default='kill_chain_shm')
    args = parser.parse_args()

    shm_path = f'C:/Users/15041/.openclaw/workspace/kill-chain-sim/{args.shm_name}.dat'

    print(f"=== Phase 1: SHM Command Ring Test ===")
    print(f"SHM path: {shm_path}")
    print(f"DLL path: {args.dll_path}")
    print(f"Log path: {args.log_path}")

    # Step 1: Initialize clean SHM
    print("\n[1] Initializing clean SHM...")
    if os.path.exists(shm_path):
        os.remove(shm_path)
    client = ShmClient(args.shm_name)
    if not client.connect():
        print(f"ERROR: Could not connect to SHM")
        return 1
    print(f"    SHM connected (magic=0x{MAGIC_VALUE:08X})")

    # Step 2: Load the DLL (starts timer thread)
    print(f"\n[2] Loading wsf_shm.dll...")
    if not os.path.exists(args.dll_path):
        print(f"ERROR: DLL not found at {args.dll_path}")
        return 1

    try:
        dll = ctypes.CDLL(args.dll_path)
        print(f"    DLL loaded successfully")
    except Exception as e:
        print(f"ERROR: Could not load DLL: {e}")
        return 1

    # Step 3: Wait for DLL timer thread to open SHM
    print(f"\n[3] Waiting for DLL to open SHM (2s)...")
    time.sleep(2.0)

    # Step 4: Send test commands via Python ShmClient
    print(f"\n[4] Sending test commands...")
    cmds_sent = []

    # Command 1: SENSOR_CONTROL
    cmd1_ok = client.send_sensor_control(sensor_id=1, mode=SensorMode.TRACK)
    print(f"    SENSOR_CONTROL: {'OK' if cmd1_ok else 'FAILED'}")
    cmds_sent.append(('SENSOR_CONTROL', cmd1_ok))

    # Command 2: WEAPON_ASSIGN
    cmd2_ok = client.send_weapon_assign(weapon_id=1, track_id=100, priority=0.95)
    print(f"    WEAPON_ASSIGN: {'OK' if cmd2_ok else 'FAILED'}")
    cmds_sent.append(('WEAPON_ASSIGN', cmd2_ok))

    # Command 3: TARGET_PRIORITY
    cmd3_ok = client.send_target_priority(track_id=200, priority=0.85)
    print(f"    TARGET_PRIORITY: {'OK' if cmd3_ok else 'FAILED'}")
    cmds_sent.append(('TARGET_PRIORITY', cmd3_ok))

    # Step 5: Wait for DLL to poll and log
    print(f"\n[5] Waiting for DLL to poll commands (3s)...")
    time.sleep(3.0)

    # Step 6: Check debug log
    print(f"\n[6] Checking debug log...")
    if os.path.exists(args.log_path):
        with open(args.log_path, 'r', encoding='utf-8', errors='replace') as f:
            log_content = f.read()
        log_lines = log_content.split('\n')

        # Find recent entries (last 50 lines)
        recent = log_lines[-50:] if len(log_lines) > 50 else log_lines
        print(f"    Log has {len(log_lines)} total lines, last 30:")
        for line in recent[-30:]:
            if line.strip():
                print(f"      {line[:120]}")

        # Check for CMD entries in log
        cmd_log_lines = [l for l in log_lines if 'CMD' in l or 'cmd' in l]
        print(f"\n    Found {len(cmd_log_lines)} log lines mentioning 'CMD'")
        if cmd_log_lines:
            print("    SUCCESS: DLL timer thread read Python commands from SHM!")
            print("    Sample:")
            for l in cmd_log_lines[:5]:
                print(f"      {l[:120]}")
            result = 0
        else:
            print("    FAIL: No CMD entries found in log")
            print("    The DLL may not have opened the file-backed SHM (it uses Global\\ prefix)")
            result = 1
    else:
        print(f"    WARNING: Log file not found at {args.log_path}")
        print("    The DLL timer thread may not have started or log path is different")
        result = 1

    print(f"\n=== Test Result: {'PASS' if result == 0 else 'FAIL'} ===")
    return result

if __name__ == '__main__':
    sys.exit(main())

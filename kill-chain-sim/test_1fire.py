#!/usr/bin/env python3
"""Quick 1-fire test: write one FIRE command and check if hit/miss appears in stderr"""
import time, os, subprocess
from pathlib import Path

WORKSPACE = Path("C:/Users/15041/.openclaw/workspace/kill-chain-sim")
CMD_FILE = WORKSPACE / "kill_chain_np_cmd.txt"
ACK_FILE = WORKSPACE / "kill_chain_np_ack.txt"
AFSIM = "D:/afsim-2.9.0-win64/bin/mission.exe"
SCENARIO = "C:/Users/15041/.openclaw/workspace/kill-chain-sim/src/sim/kill_chain_np_multi.txt"

# Clean up
for f in [CMD_FILE, ACK_FILE]:
    if f.exists():
        f.unlink()

# Start AFSIM in background, capturing stderr
print("[TEST] Starting AFSIM...")
proc = subprocess.Popen(
    [AFSIM, "-rt", "-fio", SCENARIO],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=False,
    cwd=str(Path(SCENARIO).resolve().parent)
)

# Wait for targets to appear in tracks
print("[TEST] Waiting for tracks...")
time.sleep(25)  # wait for first target (asm1) to spawn at t=20s

# Write one FIRE command
if CMD_FILE.exists():
    CMD_FILE.unlink()
CMD_FILE.write_text("FIRE:aim120_sim_1:radar1:1\n", encoding="utf-8")
print("[TEST] FIRE sent: aim120_sim_1 -> track 1")

# Wait for result
time.sleep(30)

# Read output so far
output = b""
while True:
    chunk = proc.stdout.read(1024)
    if not chunk:
        break
    output += chunk

print("\n=== Relevant stderr output ===")
for line in output.decode('utf-8', errors='replace').split('\n'):
    if any(k in line for k in ["WEAPON_FIRED", "WEAPON_HIT", "WEAPON_MISS", "KCMD", "Result", "KILLED", "miss", "track"]):
        print(line)

proc.terminate()
proc.wait()
print("\n[TEST] Done")

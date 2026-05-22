"""Test EVT parsing standalone."""
import sys

EVT_PATH = r"C:\Users\15041\.openclaw\workspace\kill-chain-sim\output\kill_chain_np_multi.evt"
ACK_PATH = r"C:\Users\15041\.openclaw\workspace\kill-chain-sim\kill_chain_np_ack.txt"

kills = 0
misses = 0

with open(EVT_PATH, 'rb') as f:
    content = f.read().decode('latin-1')

# Join continuation lines (backslash followed by CRLF on Windows)
content = content.replace(chr(92) + "\r\n", " ")

for line in content.split("\n"):
    if not line.strip():
        continue
    if "WEAPON_HIT" in line and "Result: KILLED" in line:
        kills += 1
        print(f"  KILL: {line[:150]}")
    elif "WEAPON_MISSED" in line:
        misses += 1
        print(f"  MISS: {line[:150]}")

print(f"\nTotal: kills={kills} misses={misses}")

"""Debug parse_evt_for_kills()."""
import os

EVT_PATH = r"C:\Users\15041\.openclaw\workspace\kill-chain-sim\src\sim\output\kill_chain_np_multi.evt"
ACK_PATH = r"C:\Users\15041\.openclaw\workspace\kill-chain-sim\kill_chain_np_ack.txt"

print(f"EVT exists: {os.path.exists(EVT_PATH)}")

if os.path.exists(EVT_PATH):
    content = open(EVT_PATH, 'rb').read().decode('latin-1')
    print(f"EVT size: {len(content)} bytes")
    print(f"Has KILLED: {'KILLED' in content}")
    print(f"Has WEAPON_HIT: {'WEAPON_HIT' in content}")
    print(f"First 200 chars: {repr(content[:200])}")

    # Test the replace
    content2 = content.replace(chr(92) + "\r\n", " ")
    print(f"\nAfter replace, KILLED in content: {'KILLED' in content2}")
    kills = sum(1 for line in content2.split("\n") if "WEAPON_HIT" in line and "Result: KILLED" in line)
    print(f"Kills found: {kills}")

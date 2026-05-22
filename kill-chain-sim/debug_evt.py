content = open('output/kill_chain_np_multi.evt', 'rb').read()
print(repr(content[:300]))
print('---')
lines = content.split(b'\n')
for i, line in enumerate(lines[:10]):
    print(f"line {i}: {repr(line[:100])}")

# Check what the fire controller sees
print("\n=== Fire controller EVT parse ===")
EVT_FILE = 'output/kill_chain_np_multi.evt'
content_str = open(EVT_FILE, 'r', encoding='utf-8').read()
# Join continuation lines
content_fixed = content_str.replace(chr(92) + "\n", " ")
print(f"Total lines after fix: {len(content_fixed.split(chr(92)))}")
hits = [l for l in content_fixed.split('\n') if 'WEAPON_HIT' in l and 'KILLED' in l]
misses = [l for l in content_fixed.split('\n') if 'WEAPON_MISSED' in l]
print(f"Hits: {len(hits)}, Misses: {len(misses)}")
for h in hits[:3]:
    print(f"  HIT: {h[:120]}")

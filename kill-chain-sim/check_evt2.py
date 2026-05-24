import re
data = open('output/kill_chain_np_multi.evt', 'rb').read()
text = data.decode('utf-8', errors='replace')

# Join continuation lines
content = re.sub(r'\\\r?\n', ' ', text)

print("=== Lines with KILLED ===")
for i, line in enumerate(content.split('\n')):
    if 'KILLED' in line:
        print(f"  [{i}] {repr(line[:150])}")

print("\n=== Pattern matching ===")
# Try the pattern used in fire_controller
m = re.search(r'INTENDED_TARGET Damage_Factor:\d+\s+Result:\s*KILLED', content)
print(f"Pattern1 (no space): {m}")

m2 = re.search(r'INTENDED_TARGET Damage_Factor: \d+ Result: KILLED', content)
print(f"Pattern2 (with space): {m2}")

# Try the exact pattern from the code
m3 = re.search(r'INTENDED_TARGET Damage_Factor:\d+\s+Result:\s*KILLED', content)
print(f"Pattern3: {m3}")

# Find lines containing both WEAPON_HIT and KILLED after join
print("\n=== WEAPON_HIT + KILLED lines ===")
for line in content.split('\n'):
    if 'WEAPON_HIT' in line and 'KILLED' in line:
        print(f"  {repr(line[:200])}")
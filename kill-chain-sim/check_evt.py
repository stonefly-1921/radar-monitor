data = open("output/kill_chain_np_multi.evt", "rb").read()
print(f"File size: {len(data)} bytes")
# Find backslash
idx = data.find(b'\\')
if idx >= 0:
    print(f"First backslash at byte {idx}")
    print(f"Context: {data[max(0,idx-5):idx+15]}")
    print(f"Hex: {data[max(0,idx-5):idx+15].hex()}")
else:
    print("No backslash found")
    idx2 = data.find(b'\r')
    print(f"First CR at: {idx2}")
# Show lines near killed
text = data.decode('utf-8', errors='replace')
for i, line in enumerate(text.split('\n')):
    if 'KILLED' in line or 'WEAPON_HIT' in line:
        print(f"Line {i}: {line[:120]}")
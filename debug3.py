with open(r'C:\Users\15041\.openclaw\workspace\MyAgent\run_10_tests.py', 'rb') as f:
    data = f.read()
lines = data.split(b'\n')
line126 = lines[125]
# Find all occurrences of triple single quotes
import re
positions = [(m.start(), m.end()) for m in re.finditer(b"'", line126)]
print("Single quote positions in line 126:", positions[:20])
print("Line 126:", line126[:80])
# Find the Chinese colons
for i, b in enumerate(line126):
    if b > 127:
        decoded = line126[max(0,i-2):i+3].decode('utf-8', errors='replace')
        if ':' in decoded or '\uff1a' in decoded:
            print(f"  Position {i}: byte={hex(b)}, context={repr(decoded)}")
            break
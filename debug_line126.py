with open(r'C:\Users\15041\.openclaw\workspace\MyAgent\run_10_tests.py', 'rb') as f:
    data = f.read()
lines = data.split(b'\n')
print(f'Total lines: {len(lines)}')
line126 = lines[125]
print(f'Line 126 ({len(line126)} bytes):')
for i in range(min(60, len(line126))):
    print(f'  byte[{i:2d}] = 0x{line126[i]:02x} = {chr(line126[i]) if 32 <= line126[i] < 127 else "?"}')
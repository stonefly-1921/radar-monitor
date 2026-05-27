with open(r'C:\Users\15041\.openclaw\workspace\MyAgent\run_10_tests.py', 'rb') as f:
    data = f.read()
lines = data.split(b'\n')
print(f'Total lines: {len(lines)}')
for i, line in enumerate(lines):
    if b"'" in line:
        print(f'Line {i+1}: {line[:80]}')
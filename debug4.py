with open(r'C:\Users\15041\.openclaw\workspace\MyAgent\run_10_tests.py', 'rb') as f:
    data = f.read()
lines = data.split(b'\n')
count = data.count(b"'''")
print(f'Total triple single quotes: {count}')
for i, line in enumerate(lines):
    if b"'''" in line:
        print(f'Line {i+1}: {repr(line[:60])}')
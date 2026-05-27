with open(r'C:\Users\15041\.openclaw\workspace\MyAgent\run_10_tests.py', 'rb') as f:
    data = f.read()
lines = data.split(b'\n')
for i in range(93, 131):
    if i < len(lines):
        line = lines[i]
        print(f'{i+1}: {repr(line[:100])}')
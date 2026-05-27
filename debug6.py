with open(r'C:\Users\15041\.openclaw\workspace\MyAgent\run_10_tests.py', 'rb') as f:
    data = f.read()
lines = data.split(b'\n')
# Check all triple quote patterns and their positions
for i, line in enumerate(lines):
    if b"'''" in line:
        print(f'Line {i+1}: {repr(line)}')
        # Also show all single quote positions
        for j, byte in enumerate(line):
            if byte == 0x27:
                print(f'  byte[{j}] = 0x27 (single quote) context: {repr(line[max(0,j-2):j+3])}')
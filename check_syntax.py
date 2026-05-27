import ast
src = open(r'C:\Users\15041\.openclaw\workspace\MyAgent\run_10_tests.py', 'rb').read()
try:
    ast.parse(src)
    print('Syntax OK')
except SyntaxError as e:
    print(f'Error at line {e.lineno}, offset {e.offset}')
    print(f'Message: {e.msg}')
    lines = src.split(b'\n')
    if e.lineno and e.lineno <= len(lines):
        line = lines[e.lineno - 1]
        print(f'Line: {repr(line[:80])}')
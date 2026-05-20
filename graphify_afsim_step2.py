import json
from pathlib import Path
from graphify.extract import collect_files, extract
import traceback

base = Path(r'D:\afsim-2.9.0-win64')
out_dir = base / 'graphify-out'

detect = json.loads((out_dir / '.graphify_detect.json').read_text(encoding='utf-8'))
code_files = detect['files']['code']
print(f'Total code files: {len(code_files)}')

# Filter to C++ files only
cpp_files = []
for f in code_files:
    p = Path(f)
    if p.suffix in ('.cpp', '.hpp', '.h', '.cc', '.cxx'):
        cpp_files.append(p)

print(f'C++ files: {len(cpp_files)}')

# Try extract on a small batch first
batch = cpp_files[:200]
print(f'Extracting {len(batch)} files...')
try:
    result = extract(batch)
    print(f'Nodes: {len(result["nodes"])}, Edges: {len(result["edges"])}')
    (out_dir / '.graphify_ast.json').write_text(json.dumps(result), encoding='utf-8')
    print('Saved to .graphify_ast.json')
except Exception as e:
    print(f'Error: {e}')
    traceback.print_exc()
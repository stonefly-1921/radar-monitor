import json
from pathlib import Path
import sys

base = Path(r'E:\radar-brain-github')
out_dir = base / 'graphify-out'
py_exec = (out_dir / '.graphify_python').read_text().strip()

# Load detect results
detect = json.loads((out_dir / '.graphify_detect.json').read_text())
code_files = detect['files']['code']

print(f"Code files: {len(code_files)}")

# Run AST extraction
import subprocess
result = subprocess.run(
    [py_exec, '-c', f"""
import sys
sys.path.insert(0, r'{base}')
from graphify.extract import collect_files, extract
from pathlib import Path
import json

code_files = {json.dumps(code_files)}
paths = []
for f in code_files:
    p = Path(f)
    paths.extend(collect_files(p) if p.is_dir() else [p])

print(f'Extracting {{len(paths)}} files...')
result = extract(paths)
(out_dir / '.graphify_ast.json').write_text(json.dumps(result))
print(f'AST: {{len(result["nodes"])}} nodes, {{len(result["edges"])}} edges')
"""],
    cwd=str(base),
    capture_output=True,
    text=True
)
print(result.stdout)
if result.returncode != 0:
    print("STDERR:", result.stderr[:500])

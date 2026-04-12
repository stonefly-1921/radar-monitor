import json
from pathlib import Path
import sys

base = Path(r'E:\radar-brain-github')
out_dir = base / 'graphify-out'

# Load AST and semantic
ast = json.loads((out_dir / '.graphify_ast.json').read_text())
sem = json.loads((out_dir / '.graphify_semantic.json').read_text())

# Merge
seen = {n['id'] for n in ast['nodes']}
merged_nodes = list(ast['nodes'])
for n in sem['nodes']:
    if n['id'] not in seen:
        merged_nodes.append(n)
        seen.add(n['id'])

merged_edges = ast['edges'] + sem['edges']
merged_hyperedges = sem.get('hyperedges', [])

merged = {
    'nodes': merged_nodes,
    'edges': merged_edges,
    'hyperedges': merged_hyperedges,
    'input_tokens': sem.get('input_tokens', 0),
    'output_tokens': sem.get('output_tokens', 0),
}
(out_dir / '.graphify_extract.json').write_text(json.dumps(merged))
print(f"Merged: {len(merged_nodes)} nodes, {len(merged_edges)} edges ({len(ast['nodes'])} AST + {len(sem['nodes'])} semantic)")

# Build graph
script = f"""
import sys
sys.path.insert(0, r'{base}')
from graphify.build import build_from_json
from pathlib import Path
import json

extraction = json.loads(Path(r'{out_dir}/.graphify_extract.json').read_text())
G = build_from_json(extraction)
print(f'Graph built: {{G.number_of_nodes()}} nodes, {{G.number_of_edges()}} edges')
"""
result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print("ERR:", result.stderr[:300])

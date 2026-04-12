import json
from pathlib import Path
import subprocess
import sys

base = Path(r'E:\radar-brain-github')
out_dir = base / 'graphify-out'

# Load and merge
ast = json.loads((out_dir / '.graphify_ast.json').read_text())
sem = json.loads((out_dir / '.graphify_semantic.json').read_text())

seen = {n['id'] for n in ast['nodes']}
merged_nodes = list(ast['nodes'])
for n in sem['nodes']:
    if n['id'] not in seen:
        merged_nodes.append(n)
        seen.add(n['id'])

merged_edges = ast['edges'] + sem['edges']
merged = {
    'nodes': merged_nodes,
    'edges': merged_edges,
    'hyperedges': sem.get('hyperedges', []),
    'input_tokens': sem.get('input_tokens', 0),
    'output_tokens': sem.get('output_tokens', 0),
}
(out_dir / '.graphify_extract.json').write_text(json.dumps(merged))
print(f"Merged: {len(merged_nodes)} nodes, {len(merged_edges)} edges")

# Build graph + cluster
script = f"""
import sys
sys.path.insert(0, r'{base}')
from graphify.build import build_from_json
from graphify.cluster import cluster, score_all
from graphify.analyze import god_nodes, surprising_connections, suggest_questions
from pathlib import Path
import json

extraction = json.loads(Path(r'{out_dir}/.graphify_extract.json').read_text())
G = build_from_json(extraction)
print(f'Graph: {{G.number_of_nodes()}} nodes, {{G.number_of_edges()}} edges')

communities = cluster(G)
cohesion = score_all(G, communities)
gods = god_nodes(G)
surprises = surprising_connections(G, communities)
labels = {{cid: 'Community ' + str(cid) for cid in communities}}

analysis = {{
    'communities': {{str(k): list(v) for k, v in communities.items()}},
    'cohesion': {{str(k): v for k, v in cohesion.items()}},
    'gods': gods,
    'surprises': surprises,
}}
Path(r'{out_dir}/.graphify_analysis.json').write_text(json.dumps(analysis, indent=2))
print(f'Communities: {{len(communities)}}')
print(f'God nodes: {{gods[:5]}}')
"""
result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print("ERR:", result.stderr[:500])

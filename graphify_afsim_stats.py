import json
from pathlib import Path

out_dir = Path(r'D:\afsim-2.9.0-win64\graphify-out')
ast = json.loads((out_dir / '.graphify_ast.json').read_text(encoding='utf-8'))
print(f'Nodes: {len(ast["nodes"])}')
print(f'Edges: {len(ast["edges"])}')
print()

# Count node types
node_types = {}
for n in ast['nodes']:
    t = n.get('type', n.get('kind', 'unknown'))
    node_types[t] = node_types.get(t, 0) + 1
print('Node types:')
for t, c in sorted(node_types.items(), key=lambda x: -x[1])[:20]:
    print(f'  {t}: {c}')
print()

# Count edge types
edge_types = {}
for e in ast['edges']:
    t = e.get('relation', e.get('type', 'unknown'))
    edge_types[t] = edge_types.get(t, 0) + 1
print('Edge types:')
for t, c in sorted(edge_types.items(), key=lambda x: -x[1])[:20]:
    print(f'  {t}: {c}')
print()

# Top files by node count
file_nodes = {}
for n in ast['nodes']:
    f = n.get('source_file', 'unknown')
    file_nodes[f] = file_nodes.get(f, 0) + 1

print('Top files by node count:')
for f, c in sorted(file_nodes.items(), key=lambda x: -x[1])[:20]:
    print(f'  {c}: {f}')
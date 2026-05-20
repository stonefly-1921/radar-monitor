import json
from pathlib import Path
from graphify.extract import collect_files, extract
import traceback

base = Path(r'D:\afsim-2.9.0-win64')
out_dir = base / 'graphify-out'

detect = json.loads((out_dir / '.graphify_detect.json').read_text(encoding='utf-8'))
code_files = detect['files']['code']

# Filter to C++ files
cpp_files = []
for f in code_files:
    p = Path(f)
    if p.suffix in ('.cpp', '.hpp', '.h', '.cc', '.cxx'):
        cpp_files.append(p)

print(f'C++ files: {len(cpp_files)}')

# Extract in batches - process 2000 files (~10x more)
batch_size = 2000
all_nodes = []
all_edges = []

for i in range(0, min(len(cpp_files), 6000), batch_size):
    batch = cpp_files[i:i+batch_size]
    print(f'Processing {i+1}-{i+len(batch)} of {len(cpp_files)}...')
    try:
        result = extract(batch)
        all_nodes.extend(result['nodes'])
        all_edges.extend(result['edges'])
        print(f'  -> Nodes: {len(result["nodes"])}, Edges: {len(result["edges"])}')
    except Exception as e:
        print(f'  -> Error: {e}')
        traceback.print_exc()
        break

print(f'\nTotal: {len(all_nodes)} nodes, {len(all_edges)} edges')
print(f'Saving to .graphify_ast.json...')

ast = {'nodes': all_nodes, 'edges': all_edges, 'hyperedges': []}
(out_dir / '.graphify_ast.json').write_text(json.dumps(ast), encoding='utf-8')
print('Done!')
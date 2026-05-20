import json
from pathlib import Path
from graphify.extract import collect_files, extract
import traceback
import time

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

# Check what's already extracted
existing_nodes = set()
existing_edges = set()
try:
    ast = json.loads((out_dir / '.graphify_ast.json').read_text(encoding='utf-8'))
    for n in ast['nodes']:
        existing_nodes.add(n.get('source_file', ''))
    print(f'Already extracted: {len(existing_nodes)} files, {len(ast["nodes"])} nodes')
except:
    ast = {'nodes': [], 'edges': [], 'hyperedges': []}
    print('No existing AST found, starting fresh')

# Extract in batches
batch_size = 2000
all_nodes = []
all_edges = []
seen_files = set()

# Load existing
all_nodes.extend(ast['nodes'])
all_edges.extend(ast['edges'])
for n in ast['nodes']:
    seen_files.add(n.get('source_file', ''))

start_time = time.time()
total_batches = (len(cpp_files) + batch_size - 1) // batch_size

for i in range(0, len(cpp_files), batch_size):
    batch = cpp_files[i:i+batch_size]
    batch_num = i // batch_size + 1
    
    # Skip if all files in batch already processed
    batch_files = set(str(p) for p in batch)
    if batch_files.issubset(seen_files):
        print(f'Batch {batch_num}/{total_batches}: SKIP (already done)')
        continue
    
    elapsed = time.time() - start_time
    print(f'Batch {batch_num}/{total_batches} ({i+1}-{i+len(batch)} of {len(cpp_files)})...')
    
    try:
        result = extract(batch)
        all_nodes.extend(result['nodes'])
        all_edges.extend(result['edges'])
        for n in result['nodes']:
            seen_files.add(n.get('source_file', ''))
        print(f'  -> Nodes: {len(result["nodes"])}, Edges: {len(result["edges"])} (total: {len(all_nodes)} nodes)')
    except Exception as e:
        print(f'  -> Error: {e}')
        traceback.print_exc()
        break

print(f'\nTotal: {len(all_nodes)} nodes, {len(all_edges)} edges ({len(seen_files)} files)')
print(f'Saving to .graphify_ast.json...')

# Deduplicate by id
unique_nodes = {}
for n in all_nodes:
    unique_nodes[n['id']] = n
unique_edges = []
seen_edge_ids = set()
for e in all_edges:
    eid = f"{e.get('source','')}->{e.get('target','')}"
    if eid not in seen_edge_ids:
        seen_edge_ids.add(eid)
        unique_edges.append(e)

result_ast = {'nodes': list(unique_nodes.values()), 'edges': unique_edges, 'hyperedges': []}
(out_dir / '.graphify_ast.json').write_text(json.dumps(result_ast), encoding='utf-8')
print(f'Done! Final: {len(result_ast["nodes"])} nodes, {len(result_ast["edges"])} edges')
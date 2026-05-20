import json
from pathlib import Path

ast = json.loads(Path(r'D:\afsim-2.9.0-win64\graphify-out\.graphify_ast.json').read_text(encoding='utf-8'))

# Build node index
node_idx = {n['id']: n for n in ast['nodes']}

# Find the WsfDisInterface class node
wsfdis_node = None
for n in ast['nodes']:
    if n.get('id','') == 'wsfdisinterface':
        wsfdis_node = n
        break

if wsfdis_node:
    print(f'Found: {wsfdis_node["id"]}')
    print(f'Label: {wsfdis_node.get("label","")}')
    print(f'File: {wsfdis_node.get("source_file","")}')
    print()

# Find all contains edges FROM wsfdisinterface
print('WsfDisInterface methods/children (contains edges):')
contains_from_wsfdis = [e for e in ast['edges'] 
                         if e.get('source','') == 'wsfdisinterface' and e.get('relation','') == 'contains']
print(f'Total: {len(contains_from_wsfdis)}')
for e in contains_from_wsfdis[:40]:
    target = node_idx.get(e['target'], {})
    print(f"  {target.get('label', e['target'])} ({e['target']})")

# Also find method edges from wsfdisinterface
method_edges = [e for e in ast['edges'] 
                if e.get('source','') == 'wsfdisinterface' and e.get('relation','') == 'method']
print(f'\nMethod edges: {len(method_edges)}')
for e in method_edges[:20]:
    target = node_idx.get(e['target'], {})
    print(f"  {target.get('label', e['target'])} ({e['target']})")

# Find calls edges from wsfdisinterface
call_edges = [e for e in ast['edges'] 
              if e.get('source','') == 'wsfdisinterface' and e.get('relation','') == 'calls']
print(f'\nCalls edges: {len(call_edges)}')
for e in call_edges[:20]:
    target = node_idx.get(e['target'], {})
    print(f"  -> {target.get('label', e['target'])} ({e['target']})")

# Find all edges FROM wsfdisinterface
all_from = [e for e in ast['edges'] if e.get('source','') == 'wsfdisinterface']
rel_counts = {}
for e in all_from:
    rel_counts[e.get('relation','')] = rel_counts.get(e.get('relation',''), 0) + 1
print(f'\nAll relations from wsfdisinterface: {rel_counts}')
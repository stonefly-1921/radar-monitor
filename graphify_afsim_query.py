import json
from pathlib import Path
from collections import defaultdict

base = Path(r'D:\afsim-2.9.0-win64')
out_dir = base / 'graphify-out'

print('Loading AST...')
ast = json.loads((out_dir / '.graphify_ast.json').read_text(encoding='utf-8'))
print(f'Nodes: {len(ast["nodes"])}, Edges: {len(ast["edges"])}')

print('Building indexes...')

# Index: node_id -> node
node_idx = {n['id']: n for n in ast['nodes']}

# Index: label -> nodes (for fuzzy search)
label_idx = defaultdict(list)
for n in ast['nodes']:
    label_idx[n.get('label', '')].append(n['id'])

# Index: source_file -> node_ids
file_idx = defaultdict(list)
for n in ast['nodes']:
    f = n.get('source_file', '')
    if f:
        file_idx[f].append(n['id'])

# Index: edges by relation
edges_by_rel = defaultdict(list)
for e in ast['edges']:
    edges_by_rel[e['relation']].append(e)

# Index: calls edges for quick lookup
calls_from = defaultdict(list)
calls_to = defaultdict(list)
for e in edges_by_rel['calls']:
    calls_from[e['source']].append(e['target'])
    calls_to[e['target']].append(e['source'])

print('Indexes built!')

# --- Query helpers ---

def find_node(pattern, limit=20):
    """Find nodes by label pattern (case-insensitive substring)"""
    pattern = pattern.lower()
    results = []
    for n in ast['nodes']:
        if pattern in n.get('label', '').lower():
            results.append(n)
            if len(results) >= limit:
                break
    return results

def who_calls(target_func, limit=30):
    """Find functions that call target_func"""
    callers = calls_to.get(target_func, [])
    results = []
    for caller in callers[:limit]:
        n = node_idx.get(caller)
        if n:
            results.append(n)
    return results, len(calls_to[target_func])

def what_does(caller_func, limit=30):
    """Find functions called by caller_func"""
    callees = calls_from.get(caller_func, [])
    results = []
    for callee in callees[:limit]:
        n = node_idx.get(callee)
        if n:
            results.append(n)
    return results, len(calls_from[caller_func])

def class_methods(class_name, limit=100):
    """Find all methods/contains edges from a class node"""
    class_node = node_idx.get(class_name)
    if not class_node:
        # Try to find by label
        matches = [n for n in ast['nodes'] if class_name.lower() in n.get('label', '').lower()]
        if matches:
            class_node = matches[0]
    
    if not class_node:
        return [], 0
    
    # Find contains edges from this class
    contains_edges = [e for e in ast['edges'] 
                     if e.get('relation') == 'contains' and e['source'] == class_node['id']]
    
    methods = []
    for e in contains_edges:
        n = node_idx.get(e['target'])
        if n:
            methods.append(n)
    
    return methods, len(contains_edges)

def file_nodes(source_file_pattern, limit=50):
    """Find files matching a pattern"""
    results = []
    for f in file_idx:
        if source_file_pattern.lower() in f.lower():
            node_count = len(file_idx[f])
            results.append((f, node_count))
            if len(results) >= limit:
                break
    return sorted(results, key=lambda x: -x[1])

def search_dis(limit=30):
    """Find DIS-related nodes"""
    results = []
    for n in ast['nodes']:
        label = n.get('label', '').lower()
        if 'dis' in label or 'pdu' in label or 'entity_state' in label:
            results.append(n)
            if len(results) >= limit:
                break
    return results

# --- Run some example queries ---
print('\n=== Example Queries ===\n')

print('1. DIS-related nodes:')
for n in search_dis(15):
    print(f"   {n['id']}  [{n.get('source_file','').split('/')[-1] if n.get('source_file') else '?'}]")

print('\n2. WsfDisInterface methods:')
methods, total = class_methods('WsfDisInterface')
print(f'   Total: {total} methods')
for m in methods[:20]:
    print(f"   {m['id']}")

print('\n3. Who calls send_entity_state_pdu?')
callers, total = who_calls('send_entity_state_pdu')
print(f'   Total callers: {total}')
for c in callers[:10]:
    print(f"   {c['id']}")

print('\n4. What does WsfDisInterface.send do?')
callees, total = what_does('WsfDisInterface.send')
print(f'   Total callees: {total}')
for c in callees[:15]:
    print(f"   {c['id']}")

print('\n5. Files in core/wsf module:')
for f, count in file_nodes('core/wsf', 10):
    print(f"   {count}: {f.split('/')[-1]}")

print('\n6. Search for "platform":')
for n in find_node('platform', 10):
    print(f"   {n['id']}  [{n.get('source_file','').split('/')[-1] if n.get('source_file') else '?'}]")
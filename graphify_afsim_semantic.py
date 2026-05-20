import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

base = Path(r'D:\afsim-2.9.0-win64')
out_dir = base / 'graphify-out'

detect = json.loads((out_dir / '.graphify_detect.json').read_text(encoding='utf-8'))
doc_files = detect['files']['document']
print(f'Doc files: {len(doc_files)}')

# Filter to text-based docs (markdown, txt, etc.)
text_docs = []
for f in doc_files:
    p = Path(f)
    if p.suffix.lower() in ('.md', '.txt', '.rst', '.adoc', '.tex'):
        text_docs.append(p)

print(f'Text docs: {len(text_docs)}')

# Load existing data
try:
    ast = json.loads((out_dir / '.graphify_ast.json').read_text(encoding='utf-8'))
    print(f'Existing AST: {len(ast["nodes"])} nodes')
except:
    ast = {'nodes': [], 'edges': [], 'hyperedges': []}
    print('No existing AST')

all_nodes = list(ast['nodes'])
all_edges = list(ast['edges'])
all_hyperedges = list(ast.get('hyperedges', []))

py_exec = sys.executable
start_time = time.time()

for i, doc_path in enumerate(text_docs):
    if i % 50 == 0:
        elapsed = time.time() - start_time
        rate = (i+1) / elapsed if elapsed > 0 else 0
        remaining = (len(text_docs) - i) / rate if rate > 0 else 0
        print(f'Processing {i+1}/{len(text_docs)} ({elapsed:.0f}s elapsed, ~{remaining:.0f}s remaining)')
    
    full_path = base / doc_path
    if not full_path.exists():
        continue
    
    try:
        content = full_path.read_text(encoding='utf-8', errors='ignore')
    except:
        continue
    
    script = f"""
import sys
from pathlib import Path
import json
import re

content = Path(r'{full_path}').read_text(encoding='utf-8', errors='ignore')

nodes = []
edges = []
hyperedges = []

# Extract headers as concept nodes
import re
for i, line in enumerate(content.split('\\n')):
    stripped = line.strip()
    if stripped.startswith('# ') or stripped.startswith('## '):
        level = len(line) - len(line.lstrip('#'))
        header = stripped.lstrip('#').strip()
        if header and len(header) > 1:
            node_id = 'doc_' + re.sub(r'[^a-zA-Z0-9]', '_', header.lower())[:50]
            nodes.append({{
                'id': node_id,
                'label': header,
                'type': 'document_header',
                'file_type': 'document',
                'source_file': r'{doc_path}',
                'source_location': f'line {{i}}',
                'captured_at': None,
                'author': None,
                'contributor': None
            }})

# Extract **bold** as important concepts
for match in re.finditer(r'\\*\\*([^*]+)\\*\\*', content):
    term = match.group(1).strip()
    if len(term) > 3 and not term.startswith('http'):
        node_id = 'doc_' + re.sub(r'[^a-zA-Z0-9]', '_', term.lower())[:40]
        if not any(n['id'] == node_id for n in nodes):
            nodes.append({{
                'id': node_id,
                'label': term,
                'type': 'concept',
                'file_type': 'document',
                'source_file': r'{doc_path}',
                'source_location': None,
                'captured_at': None,
                'author': None,
                'contributor': None
            }})

# Link headers in hierarchy
prev_header = None
for node in nodes:
    if node['type'] == 'document_header':
        if prev_header:
            edges.append({{
                'source': prev_header,
                'target': node['id'],
                'relation': 'contains',
                'confidence': 'EXTRACTED',
                'confidence_score': 1.0,
                'source_file': r'{doc_path}',
                'source_location': None,
                'weight': 1.0
            }})
        prev_header = node['id']

print(json.dumps({{'nodes': nodes, 'edges': edges}}))
"""
    
    try:
        r = subprocess.run([py_exec, '-c', script], capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            output = r.stdout.strip()
            if output:
                try:
                    result = json.loads(output)
                    all_nodes.extend(result['nodes'])
                    all_edges.extend(result['edges'])
                except:
                    pass
    except Exception as e:
        pass

print(f'\\nDoc semantic complete: {len(all_nodes)} total nodes, {len(all_edges)} total edges')

# Deduplicate
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

result_ast = {'nodes': list(unique_nodes.values()), 'edges': unique_edges, 'hyperedges': all_hyperedges}
(out_dir / '.graphify_ast.json').write_text(json.dumps(result_ast), encoding='utf-8')
print(f'Final: {len(result_ast["nodes"])} nodes, {len(result_ast["edges"])} edges')
print('Saved to .graphify_ast.json')
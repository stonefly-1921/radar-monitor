import json
from pathlib import Path
import subprocess
import sys

base = Path(r'E:\radar-brain-github')
out_dir = base / 'graphify-out'
py_exec = (out_dir / '.graphify_python').read_text().strip()

detect = json.loads((out_dir / '.graphify_detect.json').read_text())
doc_files = detect['files']['document']
print(f"Doc files to extract: {doc_files}")

all_nodes = []
all_edges = []
all_hyperedges = []

for doc_path in doc_files:
    full_path = base / doc_path
    if not full_path.exists():
        print(f"  SKIP (not found): {doc_path}")
        continue
    
    content = full_path.read_text(encoding='utf-8')
    print(f"  Processing {doc_path} ({len(content)} chars)...")
    
    # Use graphify's semantic extraction via subprocess
    script = f"""
import sys
sys.path.insert(0, r'{base}')
from pathlib import Path
import json

content = Path(r'{full_path}').read_text(encoding='utf-8')

# Simple extraction: extract concepts and relationships from markdown docs
nodes = []
edges = []
hyperedges = []

# Extract headers as concept nodes
import re
for i, line in enumerate(content.split('\\n')):
    if line.startswith('# ') or line.startswith('## '):
        level = len(line) - len(line.lstrip('#'))
        header = line.lstrip('#').strip()
        # Create node ID from header
        node_id = header.lower().replace(' ', '_').replace('-', '_')
        nodes.append({{
            'id': f'doc_{{node_id}}',
            'label': header,
            'file_type': 'document',
            'source_file': r'{doc_path}',
            'source_location': f'line {{i}}',
            'captured_at': None,
            'author': None,
            'contributor': None
        }})
    
    # Extract **bold** as important concepts
    for match in re.finditer(r'\*\*([^*]+)\*\*', content):
        term = match.group(1).strip()
        if len(term) > 3 and not term.startswith('http'):
            node_id = 'doc_' + term.lower().replace(' ', '_').replace('-', '_')[:40]
            if not any(n['id'] == node_id for n in nodes):
                nodes.append({{
                    'id': node_id,
                    'label': term,
                    'file_type': 'document',
                    'source_file': r'{doc_path}',
                    'source_location': None,
                    'captured_at': None,
                    'author': None,
                    'contributor': None
                }})

# Create edges between headers (hierarchy)
prev_header = None
for node in nodes:
    if prev_header and node['id'] != prev_header['id']:
        edges.append({{
            'source': prev_header['id'],
            'target': node['id'],
            'relation': 'contains',
            'confidence': 'EXTRACTED',
            'confidence_score': 1.0,
            'source_file': r'{doc_path}',
            'source_location': None,
            'weight': 1.0
        }})
    prev_header = node

result = {{'nodes': nodes, 'edges': edges, 'hyperedges': [], 'input_tokens': len(content), 'output_tokens': 0}}
print(json.dumps(result))
"""
    
    r = subprocess.run([py_exec, '-c', script], capture_output=True, text=True)
    if r.returncode == 0:
        try:
            result = json.loads(r.stdout.strip().split('\n')[-1])
            all_nodes.extend(result['nodes'])
            all_edges.extend(result['edges'])
            print(f"    -> {len(result['nodes'])} nodes")
        except:
            print(f"    -> FAILED to parse: {r.stdout[:100]}")
    else:
        print(f"    -> FAILED: {r.stderr[:200]}")

# Save semantic results
semantic = {
    'nodes': all_nodes,
    'edges': all_edges,
    'hyperedges': all_hyperedges,
    'input_tokens': sum(f.read_text(encoding='utf-8').__len__() for f in [base/p for p in doc_files if (base/p).exists()]),
    'output_tokens': 0
}
(out_dir / '.graphify_semantic.json').write_text(json.dumps(semantic))
print(f"\nSemantic complete: {len(all_nodes)} nodes, {len(all_edges)} edges")

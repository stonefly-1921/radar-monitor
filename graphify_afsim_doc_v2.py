import json
from pathlib import Path
import re
import time

base = Path(r'D:\afsim-2.9.0-win64')
out_dir = base / 'graphify-out'

detect = json.loads((out_dir / '.graphify_detect.json').read_text(encoding='utf-8'))
doc_files = detect['files']['document']
print(f'Doc files: {len(doc_files)}')

# Filter to text-based docs
text_docs = []
for f in doc_files:
    p = Path(f)
    if p.suffix.lower() in ('.md', '.txt', '.rst', '.adoc', '.tex', '.cmake', '.cfg', '.in', '.out'):
        text_docs.append(p)

print(f'Text docs: {len(text_docs)}')

# Load existing AST
ast = json.loads((out_dir / '.graphify_ast.json').read_text(encoding='utf-8'))
print(f'Existing AST: {len(ast["nodes"])} nodes, {len(ast["edges"])} edges')

all_nodes = list(ast['nodes'])
all_edges = list(ast['edges'])
existing_node_ids = set(n['id'] for n in ast['nodes'])
existing_edge_keys = set(f"{e.get('source','')}->{e.get('target','')}" for e in ast['edges'])

start_time = time.time()
doc_node_count = 0
doc_edge_count = 0

for i, doc_path in enumerate(text_docs):
    if i % 200 == 0:
        elapsed = time.time() - start_time
        rate = (i+1) / elapsed if elapsed > 0 else 0
        remaining = (len(text_docs) - i) / rate if rate > 0 else 0
        print(f'{i+1}/{len(text_docs)} ({elapsed:.0f}s elapsed, ~{remaining:.0f}s remaining) - doc nodes: {doc_node_count}')
    
    full_path = base / doc_path
    if not full_path.exists():
        continue
    
    try:
        content = full_path.read_text(encoding='utf-8', errors='ignore')
    except:
        continue
    
    if len(content) < 10:
        continue
    
    doc_nodes = []
    doc_edges = []
    headers = []
    
    # Extract headers
    for line_num, line in enumerate(content.split('\n')):
        stripped = line.strip()
        if stripped.startswith('# ') or stripped.startswith('## ') or stripped.startswith('### '):
            level = len(line) - len(line.lstrip('#'))
            header = stripped.lstrip('#').strip()
            if header and len(header) > 1 and len(header) < 200:
                header_id = f"doc_{re.sub(r'[^a-zA-Z0-9]', '_', header.lower())[:50]}"
                if header_id not in existing_node_ids:
                    doc_nodes.append({
                        'id': header_id,
                        'label': header,
                        'type': 'document_header',
                        'file_type': 'document',
                        'source_file': str(doc_path),
                        'source_location': f'line {line_num}',
                        'captured_at': None,
                        'author': None,
                        'contributor': None
                    })
                    existing_node_ids.add(header_id)
                headers.append(header_id)
        
        # Extract **bold** as concepts
        for match in re.finditer(r'\*\*([^*]+)\*\*', stripped):
            term = match.group(1).strip()
            if len(term) > 3 and len(term) < 100 and not term.startswith('http'):
                term_id = f"doc_{re.sub(r'[^a-zA-Z0-9]', '_', term.lower())[:40]}"
                if term_id not in existing_node_ids:
                    doc_nodes.append({
                        'id': term_id,
                        'label': term,
                        'type': 'concept',
                        'file_type': 'document',
                        'source_file': str(doc_path),
                        'source_location': f'line {line_num}',
                        'captured_at': None,
                        'author': None,
                        'contributor': None
                    })
                    existing_node_ids.add(term_id)
    
    # Link consecutive headers
    for j in range(1, len(headers)):
        edge_key = f"{headers[j-1]}->{headers[j]}"
        if edge_key not in existing_edge_keys:
            doc_edges.append({
                'source': headers[j-1],
                'target': headers[j],
                'relation': 'contains',
                'confidence': 'EXTRACTED',
                'confidence_score': 1.0,
                'source_file': str(doc_path),
                'source_location': None,
                'weight': 1.0
            })
            existing_edge_keys.add(edge_key)
    
    # Link first header to file node
    if headers:
        file_node_id = f"file_{re.sub(r'[^a-zA-Z0-9]', '_', str(doc_path).lower())[:60]}"
        if file_node_id not in existing_node_ids:
            doc_nodes.append({
                'id': file_node_id,
                'label': Path(doc_path).name,
                'type': 'source_file',
                'file_type': 'document',
                'source_file': str(doc_path),
                'source_location': None,
                'captured_at': None,
                'author': None,
                'contributor': None
            })
            existing_node_ids.add(file_node_id)
        
        edge_key = f"{file_node_id}->{headers[0]}"
        if edge_key not in existing_edge_keys:
            doc_edges.append({
                'source': file_node_id,
                'target': headers[0],
                'relation': 'contains',
                'confidence': 'EXTRACTED',
                'confidence_score': 1.0,
                'source_file': str(doc_path),
                'source_location': None,
                'weight': 1.0
            })
            existing_edge_keys.add(edge_key)
    
    all_nodes.extend(doc_nodes)
    all_edges.extend(doc_edges)
    doc_node_count += len(doc_nodes)
    doc_edge_count += len(doc_edges)

print(f'\nDoc extraction complete: {doc_node_count} doc nodes, {doc_edge_count} doc edges')
print(f'Total: {len(all_nodes)} nodes, {len(all_edges)} edges')

# Save
result_ast = {'nodes': all_nodes, 'edges': all_edges, 'hyperedges': []}
(out_dir / '.graphify_ast.json').write_text(json.dumps(result_ast), encoding='utf-8')
print('Saved to .graphify_ast.json')
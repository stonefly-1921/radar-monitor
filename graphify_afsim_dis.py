import json
from pathlib import Path

ast = json.loads(Path(r'D:\afsim-2.9.0-win64\graphify-out\.graphify_ast.json').read_text(encoding='utf-8'))

# Find DisInterface nodes
dis_nodes = [n for n in ast['nodes'] if 'disinterface' in n.get('id','').lower()]
print(f'DisInterface nodes: {len(dis_nodes)}')

# Show first 10
for n in dis_nodes[:10]:
    print(f"  ID: {n['id']}")
    print(f"  Label: {n.get('label','')}")
    print(f"  File: {n.get('source_file','')}")
    print()

# Find edges FROM WsfDisInterface
print('Edges from WsfDisInterface (first 20):')
count = 0
for e in ast['edges']:
    if 'disinterface' in e.get('source','').lower():
        print(f"  {e['source']} --[{e.get('relation','')}]--> {e['target']}")
        count += 1
        if count >= 20:
            break

# Find edges TO send_entity_state_pdu
print('\nEdges TO send_entity_state_pdu:')
count = 0
for e in ast['edges']:
    if 'send_entity_state' in e.get('target','').lower():
        print(f"  {e['source']} --[{e.get('relation','')}]--> {e['target']}")
        count += 1
        if count >= 10:
            break
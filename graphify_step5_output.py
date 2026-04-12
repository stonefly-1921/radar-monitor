import json
from pathlib import Path
import subprocess
import sys

base = Path(r'E:\radar-brain-github')
out_dir = base / 'graphify-out'

# Load analysis
analysis = json.loads((out_dir / '.graphify_analysis.json').read_text())
communities = {int(k): v for k, v in analysis['communities'].items()}
cohesion = {int(k): v for k, v in analysis['cohesion'].items()}
gods = analysis['gods']
surprises = analysis['surprises']

# Label communities manually based on god nodes
labels = {}
for cid, nodes in communities.items():
    node_ids = set(nodes)
    # Find god nodes in this community
    community_gods = [g for g in gods if g['id'] in node_ids]
    if community_gods:
        labels[cid] = community_gods[0]['label']
    else:
        labels[cid] = f"Community {cid}"

print("Community labels:")
for cid, label in sorted(labels.items()):
    print(f"  {cid}: {label} ({len(communities[cid])} nodes)")

# Save labels
(out_dir / '.graphify_labels.json').write_text(json.dumps({str(k): v for k, v in labels.items()}))

# Generate HTML
script = f"""
import sys
sys.path.insert(0, r'{base}')
from graphify.build import build_from_json
from graphify.export import to_html, to_json
from pathlib import Path
import json

extraction = json.loads(Path(r'{out_dir}/.graphify_extract.json').read_text())
analysis = json.loads(Path(r'{out_dir}/.graphify_analysis.json').read_text())
labels_raw = json.loads(Path(r'{out_dir}/.graphify_labels.json').read_text())

G = build_from_json(extraction)
communities = {{int(k): v for k, v in analysis['communities'].items()}}
labels = {{int(k): v for k, v in labels_raw.items()}}

to_html(G, communities, r'{out_dir}/graph.html', community_labels=labels)
print('HTML written')

to_json(G, communities, r'{out_dir}/graph.json')
print('JSON written')
"""
result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print("ERR:", result.stderr[:500])

# Generate report
script2 = f"""
import sys
sys.path.insert(0, r'{base}')
from graphify.build import build_from_json
from graphify.report import generate
from pathlib import Path
import json

extraction = json.loads(Path(r'{out_dir}/.graphify_extract.json').read_text())
analysis = json.loads(Path(r'{out_dir}/.graphify_analysis.json').read_text())
labels_raw = json.loads(Path(r'{out_dir}/.graphify_labels.json').read_text())
detection = json.loads(Path(r'{out_dir}/.graphify_detect.json').read_text())

G = build_from_json(extraction)
communities = {{int(k): v for k, v in analysis['communities'].items()}}
cohesion = {{int(k): v for k, v in analysis['cohesion'].items()}}
labels = {{int(k): v for k, v in labels_raw.items()}}
gods = analysis['gods']
surprises = analysis['surprises']
tokens = {{'input': extraction.get('input_tokens', 0), 'output': extraction.get('output_tokens', 0)}}

report = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, r'{base}')
Path(r'{out_dir}/GRAPH_REPORT.md').write_text(report)
print('Report written')
"""
result2 = subprocess.run([sys.executable, '-c', script2], capture_output=True, text=True)
print(result2.stdout)
if result2.returncode != 0:
    print("ERR:", result2.stderr[:500])

print("\nDone! Outputs in:", out_dir)
print("  graph.html - open in browser")
print("  graph.json - raw graph data")
print("  GRAPH_REPORT.md - audit report")

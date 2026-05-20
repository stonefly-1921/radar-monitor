import json
from pathlib import Path
from graphify.extract import collect_files, extract
import traceback
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
    if p.suffix.lower() in ('.md', '.txt', '.rst', '.adoc', '.tex'):
        text_docs.append(p)

print(f'Text docs: {len(text_docs)}')

# Test with first doc
test_path = text_docs[0]
print(f'Test file: {test_path}')
print(f'Exists: {(base / test_path).exists()}')

try:
    content = (base / test_path).read_text(encoding='utf-8', errors='ignore')
    print(f'Content length: {len(content)}')
    print(f'First 200 chars: {content[:200]}')
except Exception as e:
    print(f'Error: {e}')
    traceback.print_exc()
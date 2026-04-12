from graphify.detect import detect
from pathlib import Path
import json
import sys

base = Path(r'E:\radar-brain-github')
out_dir = base / 'graphify-out'
out_dir.mkdir(exist_ok=True)

result = detect(base)
(out_dir / '.graphify_detect.json').write_text(json.dumps(result))

print(f"Corpus: {result['total_files']} files ~ {result['total_words']} words")
for k, v in result['files'].items():
    if v:
        print(f"  {k}: {len(v)} files")

# Write python path
(open(out_dir / '.graphify_python', 'w')).write(sys.executable)
print("Python:", sys.executable)

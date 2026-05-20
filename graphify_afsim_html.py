import json
from pathlib import Path

base = Path(r'D:\afsim-2.9.0-win64')
out_dir = base / 'graphify-out'

# Load AST
ast = json.loads((out_dir / '.graphify_ast.json').read_text(encoding='utf-8'))

print(f'Building HTML with {len(ast["nodes"])} nodes...')

# Build node index
nodes = {n['id']: n for n in ast['nodes']}

# Find top calling functions
calls_from = {}
calls_to = {}
for e in ast['edges']:
    if e.get('relation') == 'calls':
        src = e.get('source', '')
        tgt = e.get('target', '')
        calls_from[src] = calls_from.get(src, 0) + 1
        calls_to[tgt] = calls_to.get(tgt, 0) + 1

top_callers = sorted(calls_from.items(), key=lambda x: -x[1])[:30]
top_callees = sorted(calls_to.items(), key=lambda x: -x[1])[:30]

# Find most used header files
includes = {}
for e in ast['edges']:
    if e.get('relation') == 'imports':
        tgt = e.get('target', '')
        includes[tgt] = includes.get(tgt, 0) + 1

top_includes = sorted(includes.items(), key=lambda x: -x[1])[:30]

# Module breakdown
modules = {}
for n in ast['nodes']:
    f = n.get('source_file', '')
    if f:
        parts = f.replace('\\', '/').split('/')
        if 'afsim-2.9.0-win64' in parts:
            idx = parts.index('afsim-2.9.0-win64')
            if idx + 2 < len(parts):
                module = parts[idx + 2]
            else:
                module = 'root'
        else:
            module = 'other'
    else:
        module = 'unknown'
    modules[module] = modules.get(module, 0) + 1

top_modules = sorted(modules.items(), key=lambda x: -x[1])[:20]

# Build HTML
html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>AFSIM 代码图谱</title>
<style>
body { font-family: -apple-system, Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }
h1 { color: #00d4ff; }
h2 { color: #ff6b6b; margin-top: 30px; }
h3 { color: #ffd93d; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; }
th, td { border: 1px solid #333; padding: 8px 12px; text-align: left; }
th { background: #333; color: #00d4ff; }
tr:nth-child(even) { background: #2a2a4a; }
tr:hover { background: #3a3a5a; }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }
.stat-box { background: #2a2a4a; padding: 15px; border-radius: 8px; text-align: center; }
.stat-box .num { font-size: 2em; color: #00d4ff; font-weight: bold; }
.stat-box .label { color: #888; }
.module-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.module-box { background: #2a2a4a; padding: 10px; border-radius: 5px; }
.module-box .name { color: #ffd93d; }
.module-box .count { color: #888; font-size: 0.9em; }
a { color: #00d4ff; }
.footer { margin-top: 40px; color: #666; font-size: 0.8em; }
</style>
</head>
<body>
<h1>AFSIM 代码图谱</h1>

<div class="stats">
<div class="stat-box"><div class="num">94,825</div><div class="label">总节点</div></div>
<div class="stat-box"><div class="num">188,877</div><div class="label">总边</div></div>
<div class="stat-box"><div class="num">18,666</div><div class="label">源文件</div></div>
<div class="stat-box"><div class="num">17,243</div><div class="label">C++ 文件</div></div>
</div>

<h2>模块分布</h2>
<div class="module-grid">
"""

for m, c in top_modules:
    pct = c / len(ast['nodes']) * 100
    html += f'<div class="module-box"><div class="name">{m}</div><div class="count">{c:,} 节点 ({pct:.1f}%)</div></div>\n'

html += """
</div>

<h2>被调用最多的函数（Top 30）</h2>
<table>
<tr><th>调用次数</th><th>函数</th></tr>
"""

for func, count in top_callees:
    html += f'<tr><td>{count}</td><td><code>{func}</code></td></tr>\n'

html += """
</table>

<h2>调用最多外部函数的函数（Top 30）</h2>
<table>
<tr><th>调用次数</th><th>函数</th></tr>
"""

for func, count in top_callers:
    html += f'<tr><td>{count}</td><td><code>{func}</code></td></tr>\n'

html += """
</table>

<h2>被包含最多的头文件（Top 30）</h2>
<table>
<tr><th>包含次数</th><th>头文件</th></tr>
"""

for hdr, count in top_includes:
    html += f'<tr><td>{count}</td><td><code>{hdr}</code></td></tr>\n'

html += """
</table>

<div class="footer">
<p>由 Graphify 生成 | 数据文件: <code>D:\afsim-2.9.0-win64\graphify-out\.graphify_ast.json</code></p>
</div>

</body>
</html>
"""

(out_dir / 'graph.html').write_text(html, encoding='utf-8')
print(f'HTML written to {out_dir / "graph.html"}')
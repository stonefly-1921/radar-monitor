import json
from pathlib import Path
import sys

base = Path(r'D:\afsim-2.9.0-win64')
out_dir = base / 'graphify-out'

# Load AST
ast = json.loads((out_dir / '.graphify_ast.json').read_text(encoding='utf-8'))
detect = json.loads((out_dir / '.graphify_detect.json').read_text(encoding='utf-8'))

print(f'AST: {len(ast["nodes"])} nodes, {len(ast["edges"])} edges')

# Count node types
node_types = {}
for n in ast['nodes']:
    t = n.get('type', 'unknown')
    node_types[t] = node_types.get(t, 0) + 1

edge_types = {}
for e in ast['edges']:
    t = e.get('relation', 'unknown')
    edge_types[t] = edge_types.get(t, 0) + 1

# Top files by node count
file_nodes = {}
for n in ast['nodes']:
    f = n.get('source_file', '')
    if f:
        file_nodes[f] = file_nodes.get(f, 0) + 1

top_files = sorted(file_nodes.items(), key=lambda x: -x[1])[:30]

# Module summary
modules = {}
for f in file_nodes.keys():
    parts = f.replace('\\', '/').split('/')
    if len(parts) >= 4 and 'afsim-2.9.0-win64' in parts:
        idx = parts.index('afsim-2.9.0-win64')
        if idx >= 0 and idx + 2 < len(parts):
            module = parts[idx + 2]
        else:
            module = 'root'
    else:
        module = 'other'
    modules[module] = modules.get(module, 0) + 1

top_modules = sorted(modules.items(), key=lambda x: -x[1])[:20]

# Count code files from detect
code_file_count = len(detect['files'].get('code', []))
doc_file_count = len(detect['files'].get('document', []))

# Generate report
report = f"""# AFSIM 代码图谱报告

## 总体统计

| 指标 | 数值 |
|------|------|
| 总节点数 | {len(ast['nodes']):,} |
| 总边数 | {len(ast['edges']):,} |
| 源文件数 | {len(file_nodes):,} |
| 代码文件 | {code_file_count:,} |
| 文档文件 | {doc_file_count:,} |

## 节点类型分布

| 类型 | 数量 |
|------|------|
"""

for t, c in sorted(node_types.items(), key=lambda x: -x[1]):
    report += f'| {t} | {c:,} |\n'

report += f"""
## 边类型分布

| 关系 | 数量 |
|------|------|
"""

for t, c in sorted(edge_types.items(), key=lambda x: -x[1]):
    report += f'| {t} | {c:,} |\n'

report += f"""
## 模块统计（按文件数）

| 模块 | 文件数 |
|------|--------|
"""

for m, c in top_modules:
    report += f'| {m} | {c:,} |\n'

report += f"""
## 代码最密集的文件（Top 30）

| 节点数 | 文件 |
|--------|------|
"""

for f, c in top_files:
    report += f'| {c} | {f} |\n'

report += f"""
## 边类型说明

- **imports**: #include 导入关系
- **contains**: 父子包含关系（类包含方法，文件包含类）
- **calls**: 函数调用关系
- **method**: 方法定义关系

---
*由 Graphify 生成*
"""

(out_dir / 'GRAPH_REPORT.md').write_text(report, encoding='utf-8')
print('Report written to GRAPH_REPORT.md')
print(report)
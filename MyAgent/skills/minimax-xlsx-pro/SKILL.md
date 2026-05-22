---
name: minimax-xlsx
description: >
  专业 Excel 表格生产系统。当用户需要处理表格数据、创建分析报告、生成多 sheet 工作簿时使用。
  底层依赖 MyAgent xlsx 工具（Windows COM，零外部依赖）。
  支持：多 sheet 创建、公式写入、数据读取、样式设置。
triggers:
  - Excel
  - 表格
  - 数据分析
  - 工作簿
  - 电子表格
  - xlsx
  - 创建报表
  - 数据处理
version: 2.0.0
metadata: {"openclaw": {"emoji": "📊"}}
dependencies: none
---

# MiniMax XLSX - 专业表格生产系统

## 底层工具（Basic Tools）

| 工具 | 能力 |
|------|------|
| `xlsx_create` | 创建 Excel 工作簿，支持多 sheet、表头、数据行 |
| `xlsx_write` | 写入单元格（支持 Excel 公式字符串）|
| `xlsx_read` | 读取 sheet 数据（Tab 分隔文本）|

> ⚠️ **不要** 使用 openpyxl、pandas。这些需要外部安装。直接调用上面列出的工具。

## 工作流程

### Phase 1 — 理解任务

1. 明确数据结构：有多少 sheet、每个 sheet 的列、数据量
2. 确认输出路径
3. 规划 sheet 数量和内容

### Phase 2 — 设计工作簿

为每个 sheet 规划：
- **表头**：列名列表
- **数据**：行列表，每行是值列表
- **公式**：在数据行中使用 `=开头` 的公式字符串

**公式规则**：
- 通过 `xlsx_write` 写入公式字符串（如 `=SUM(A1:A10)`）
- Excel 打开文件时会自动计算
- 支持的函数：`SUM`, `AVERAGE`, `IF`, `VLOOKUP`, `INDEX`, `MATCH`, `COUNTIF`, `SUMIF` 等标准函数

### Phase 3 — 构建工作簿

**创建多 sheet 工作簿**：

```python
xlsx_create(output_path='report.xlsx', sheets=[
    {
        'name': '销售数据',
        'headers': ['产品', '销量', '单价', '销售额'],
        'rows': [
            ['产品A', 100, 50, '=B2*C2'],
            ['产品B', 200, 80, '=B3*C3']
        ]
    },
    {
        'name': '汇总',
        'headers': ['总计销量', '总计销售额'],
        'rows': [
            ['=SUM(销售数据!B2:B100)', '=SUM(销售数据!D2:D100)']
        ]
    }
])
```

**追加写入**：

```python
# 写入标题
xlsx_write(input_path='report.xlsx', sheet_name='销售数据', cell='E1', value='利润率')
# 写入公式
xlsx_write(input_path='report.xlsx', sheet_name='销售数据', cell='E2', value='=D2/B2')
```

**跨 sheet 引用**：

```python
# 汇总 sheet 引用销售数据
xlsx_write(input_path='report.xlsx', sheet_name='汇总', cell='A1', value='=SUM(销售数据!B:B)')
```

### Phase 4 — 读取验证

```python
xlsx_read(input_path='report.xlsx', sheet_name='销售数据', max_rows=100)
# 返回 {'success': True, 'rows': ['产品\t销量\t单价\t销售额', '产品A\t100\t50\t5000', ...], 'count': N}
```

## Excel 公式参考

### 常用公式示例

| 用途 | 公式 |
|------|------|
| 求和 | `=SUM(A1:A10)` |
| 平均值 | `=AVERAGE(B1:B10)` |
| 计数 | `=COUNTIF(A:A,">0")` |
| 条件求和 | `=SUMIF(B:B,"北京",C:C)` |
| 跨 sheet 求和 | `=SUM(销售数据!D:D)` |
| 百分比 | `=D2/SUM($D$2:$D$10)` |
| VLOOKUP | `=VLOOKUP(A2,Lookup!A:C,3,FALSE)` |
| IF 条件 | `=IF(B2>100,"高","低")` |
| 日期 | `=TODAY()`, `=NOW()` |

### 公式注意事项

- 公式字符串以 `=` 开头
- 列引用可用 `A:A` 表示整列
- 绝对引用用 `$A$1`
- 字符串内引号用双引号 `""`

## 样式指南

**表头样式**（通过 Excel 自身功能实现）：
- Excel 打开后可选中表头行设置加粗、背景色
- 通过 `xlsx_write` 写入数据时，字符串值不会被自动格式化

**建议流程**：
1. 用 `xlsx_create` 创建基础数据
2. 用 `xlsx_write` 写入公式
3. 用户用 Excel 打开后自行美化格式
4. 或者描述你的样式需求，我们会增强工具

## 错误处理

- **文件不存在**：`xlsx_read` 返回 `{"success": false, "error": "File not found"}`
- **Sheet 不存在**：返回错误信息
- **公式错误**：Excel 打开文件时会显示 `#REF!` 等错误，需检查公式引用是否正确

## 示例

### 创建财务报告

```python
# 财务数据工作簿
xlsx_create('财务报告.xlsx', sheets=[
    {
        'name': '收入明细',
        'headers': ['月份', '产品A', '产品B', '产品C', '合计'],
        'rows': [
            ['1月', 100000, 80000, 60000, '=SUM(B2:D2)'],
            ['2月', 120000, 90000, 70000, '=SUM(B3:D3)'],
            ['3月', 130000, 95000, 75000, '=SUM(B4:D4)']
        ]
    },
    {
        'name': '季度汇总',
        'headers': ['季度', '总收入', '同比'],
        'rows': [
            ['Q1', '=SUM(收入明细!E2:E4)', '=B2/前一年Q1-1'],
            ['Q2', '=SUM(收入明细!E5:E7)', '=B3/前一年Q2-1']
        ]
    }
])
```

### 创建数据分析表

```python
# 市场分析
xlsx_create('市场分析.xlsx', sheets=[
    {
        'name': '原始数据',
        'headers': ['地区', 'Q1销售', 'Q2销售', 'Q3销售', 'Q4销售'],
        'rows': [
            ['华北', 120, 135, 148, 162],
            ['华东', 98, 112, 130, 145],
            ['华南', 145, 160, 175, 190]
        ]
    },
    {
        'name': '增长率',
        'headers': ['地区', 'Q1增长', 'Q2增长', 'Q3增长', 'Q4增长'],
        'rows': [
            ['华北', '=(B2-100)/100', '=(C2-B2)/B2', '=(D2-C2)/C2', '=(E2-D2)/D2'],
            ['华东', '=(B3-100)/100', '=(C3-B3)/B3', '=(D3-C3)/C3', '=(E3-D3)/D3'],
            ['华南', '=(B4-100)/100', '=(C4-B4)/B4', '=(D4-C4)/D4', '=(E4-D4)/D4']
        ]
    }
])
```

## 限制说明

- 当前版本不支持：图表（chart）、透视表（pivot）、条件格式、样式自动化
- 如需这些功能，请描述需求，我们会持续增强工具能力
- 文件格式：标准 .xlsx，可被 Excel/WPS/LibreOffice 打开
- 公式由 Excel 计算，不需要单独运行 recalc
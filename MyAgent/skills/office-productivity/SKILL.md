---
name: office-productivity
description: >
  办公文档组合技能。当用户需要创建、编辑、格式化 Word/Excel/PPT 文档，或生成报告、填写模板、整理会议记录时使用。
  底层依赖 MyAgent 的零外部依赖 Office COM 工具（docx_* / xlsx_* / pptx_create / office_*）。
triggers:
  - 创建文档
  - 生成报告
  - 写 Word
  - 做 Excel
  - 生成 PPT
  - 办公自动化
  - 会议记录
  - 模板填充
---

# Office Productivity - 办公自动化

## 底层工具（Basic Tools）

这些是已经安装好的基本工具，直接调用，不要尝试安装额外依赖：

| 工具 | 能力 |
|------|------|
| `docx_create` | 创建 Word 文档，支持标题/段落/表格 |
| `docx_edit` | 查找替换文本 |
| `docx_read` | 读取 Word 文档文本 |
| `xlsx_create` | 创建 Excel，支持多 sheet |
| `xlsx_write` | 写入单元格 |
| `xlsx_read` | 读取 Excel 数据 |
| `pptx_create` | 创建 PPT（标题 + 内容幻灯片）|
| `office_word_to_pdf` | Word → PDF |
| `office_excel_to_pdf` | Excel → PDF |
| `office_ppt_to_pdf` | PPT → PDF |

> ⚠️ **不要** 使用 python-docx、openpyxl、python-pptx。这些需要外部安装。直接调用上面列出的工具即可。

## 工作流模式

### 📄 Word 文档

**创建文档**：
```
docx_create(output_path, title, paragraphs)
- title: 文档标题
- paragraphs: 段落列表，支持：
  - 字符串 → 普通段落
  - {'type': 'heading', 'text': '标题', 'level': 1~5} → 标题
  - {'type': 'table', 'headers': [...], 'rows': [[...]]} → 表格
```

**读取文档**：docx_read(input_path) → {content, length}

**替换文本**：
```
docx_edit(input_path, find='旧文本', replace='新文本', output_path=None)
- output_path 省略则原地修改
```

### 📊 Excel 工作簿

**创建多 sheet 工作簿**：
```
xlsx_create(output_path, sheets=[
  {'name': 'Sheet1', 'headers': ['列1','列2'], 'rows': [['A','100'], ['B','200']]},
  {'name': 'Sheet2', 'headers': [...], 'rows': [...]}
])
```

**追加写入**：
```
xlsx_write(input_path, sheet_name_or_index, cell, value)
- cell: 'A1' 格式
- sheet_name_or_index: 'Sales' 或 1（第一个sheet）
```

**读取数据**：
```
xlsx_read(input_path, sheet_name='', max_rows=100)
- sheet_name 空则读第一个 sheet
```

### 📑 PPT 演示文稿

**创建 PPT**：
```
pptx_create(output_path, title, slides=[
  {'type': 'title', 'text': '封面标题'},
  {'type': 'content', 'title': '页面标题', 'bullets': ['要点1', '要点2']},
  {'type': 'table', 'title': '数据表格', 'headers': [...], 'rows': [...]},
  {'type': 'section', 'text': '章节标题'}
])
```

### 📋 报告生成

**完整报告流程**：
1. docx_create 创建报告框架（标题、段落、表格）
2. docx_edit 填充具体数据
3. office_word_to_pdf 导出 PDF

### 📝 模板填充

**从模板创建并填充**：
1. docx_read 读取模板内容
2. docx_edit 替换占位符（如 {{name}}、{{date}}）
3. docx_create 保存新文档

## 示例

### 创建项目报告
```python
# 1. 创建报告 Word 文档
docx_create(
    output_path='report.docx',
    title='2026年Q1项目进度报告',
    paragraphs=[
        '一、项目概况',
        {'type': 'heading', 'text': '1.1 项目背景', 'level': 2},
        '本项目旨在...',
        {'type': 'table', 'headers': ['阶段','负责人','状态'], 'rows': [
            ['需求分析', '张三', '已完成'],
            ['开发', '李四', '进行中']
        ]}
    ]
)
```

### 创建数据表格 Excel
```python
xlsx_create(
    output_path='sales.xlsx',
    sheets=[
        {'name': '销售数据', 'headers': ['产品','销量','销售额'], 'rows': [
            ['产品A', 100, 50000],
            ['产品B', 200, 85000]
        ]}
    ]
)
```

### 创建演示文稿
```python
pptx_create(
    output_path='presentation.pptx',
    title='AI行业分析',
    slides=[
        {'type': 'title', 'text': '2026年AI行业分析'},
        {'type': 'content', 'title': '市场概况', 'bullets': [
            '全球AI市场规模突破3.2万亿美元',
            '企业AI采用率达到89%'
        ]},
        {'type': 'table', 'title': '核心数据', 'headers': ['指标','2025','2026'], 'rows': [
            ['市场规模', '$2.1T', '$3.2T']
        ]}
    ]
)
```

## 注意事项

- 所有 Office 工具通过 Windows COM 工作，需要目标机器安装 Microsoft Office
- PPT 创建不支持复杂布局（双栏、图表），如需高级功能请描述需求
- Excel 公式：xlsx_write 可以写入 Excel 公式字符串（如 `=SUM(A1:A10)`）
- 文件路径使用 Windows 绝对路径或相对于当前工作目录
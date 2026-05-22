---
name: minimax-docx
description: >
  专业 Word 文档创建系统。当用户需要创建报告、合同、公文、学术论文等 Word 文档时使用。
  底层依赖 MyAgent docx 工具（Windows COM，零外部依赖）。
  支持：创建文档、标题/段落/表格、文本查找替换、读取内容。
triggers:
  - Word
  - docx
  - 文档
  - 报告
  - 合同
  - 公文
  - 论文
  - 排版
  - 创建文档
version: 2.0.0
metadata: {"openclaw": {"emoji": "📄"}}
dependencies: none
---

# MiniMax DOCX - 专业文档生产系统

## 底层工具（Basic Tools）

| 工具 | 能力 |
|------|------|
| `docx_create` | 创建 Word 文档（标题/段落/表格）|
| `docx_edit` | 查找替换文本 |
| `docx_read` | 读取文档文本内容 |

> ⚠️ **不要** 使用 python-docx、C# OpenXML SDK。这些需要额外依赖。直接调用上面列出的工具。

## Pipeline 路由

根据任务类型选择路径：

```
用户任务
├─ 没有输入文件 → Pipeline A：创建新文档
│   触发词：写、创建、生成、起草、报告、合同、公文
│
├─ 有输入 .docx + 替换内容 → Pipeline B：编辑内容
│   触发词：替换、修改、编辑、填充、更新
│
└─ 有输入 .docx + 套模板样式 → Pipeline C：暂不支持
    （复杂样式/模板应用需要 OpenXML SDK，暂不提供）
```

## Pipeline A：创建新文档

### 基本用法

```
docx_create(output_path, title, paragraphs, tables, font_name, font_size)
```

**参数说明**：
- `output_path`: 输出 .docx 路径（必填）
- `title`: 文档标题（选填）
- `paragraphs`: 段落列表（选填）
  - 字符串 → 普通段落
  - `{'type': 'heading', 'text': '标题', 'level': 1~5}` → 标题
- `tables`: 表格列表（选填）
  - `{'headers': ['列1', '列2'], 'rows': [['A', 'B'], ['C', 'D']]}`

### 示例

**创建项目报告**：
```python
docx_create(
    output_path='项目报告.docx',
    title='2026年Q1项目进度报告',
    paragraphs=[
        '一、项目概况',
        {'type': 'heading', 'text': '1.1 项目背景', 'level': 2},
        '本项目旨在提升团队协作效率...',
        {'type': 'heading', 'text': '1.2 项目目标', 'level': 2},
        '项目目标包括：',
        '• 完成核心功能开发',
        '• 部署上线并稳定运行',
        {'type': 'heading', 'text': '二、进度跟踪', 'level': 2},
        {'type': 'table', 'headers': ['阶段', '负责人', '状态', '完成度'],
         'rows': [
            ['需求分析', '张三', '已完成', '100%'],
            ['系统设计', '李四', '进行中', '80%'],
            ['开发实现', '王五', '进行中', '45%']
        ]}
    ]
)
```

**创建合同**：
```python
docx_create(
    output_path='合同.docx',
    title='软件外包合同',
    paragraphs=[
        {'type': 'heading', 'text': '第一章 总则', 'level': 1},
        '第一条 合同双方',
        '甲方：[甲方名称]',
        '乙方：[乙方名称]',
        {'type': 'heading', 'text': '第二条 服务内容', 'level': 1},
        '乙方为甲方提供以下服务：',
        '1. 系统需求分析',
        '2. 系统设计与开发',
        '3. 部署与运维支持',
        {'type': 'heading', 'text': '第三章 违约责任', 'level': 1},
        '第七条 双方应严格履行本合同...'
    ]
)
```

**创建学术论文**：
```python
docx_create(
    output_path='论文.docx',
    title='基于深度学习的图像识别研究',
    paragraphs=[
        {'type': 'heading', 'text': '摘要', 'level': 1},
        '本文研究了基于深度学习的图像识别方法...',
        {'type': 'heading', 'text': '1. 引言', 'level': 2},
        '图像识别是计算机视觉的核心问题...',
        {'type': 'heading', 'text': '2. 相关工作', 'level': 2},
        '近年来，深度学习在图像识别领域取得了显著进展...',
        {'type': 'heading', 'text': '3. 方法', 'level': 2},
        '本文提出一种基于Transformer的新架构...',
        {'type': 'table', 'headers': ['方法', '准确率', '参数量'],
         'rows': [
            ['ResNet50', '76.3%', '25.6M'],
            ['本文方法', '81.5%', '22.1M']
        ]}
    ],
    font_name='宋体',
    font_size=12
)
```

## Pipeline B：编辑现有文档

### 文本替换

```
docx_edit(input_path, find, replace, output_path=None)
- output_path 省略则原地修改
```

**示例**：
```python
# 填充模板占位符
docx_edit(
    input_path='合同模板.docx',
    find='[甲方名称]',
    replace='北京科技有限公司',
    output_path='合同_已填写.docx'
)

# 批量替换
docx_edit(input_path='报告.docx', find='2025年', replace='2026年')
```

### 读取内容

```
docx_read(input_path, max_chars=10000)
→ {'success': True, 'content': '文档文本...', 'length': N}
```

```python
content = docx_read('报告.docx')
print(content['content'])
```

## 样式参考

### 字体设置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `font_name` | 字体名称 | 微软雅黑 |
| `font_size` | 字号（磅）| 11 |

### 标题级别

| level | 字号（磅）| 用途 |
|-------|---------|------|
| 1 | 22 | 一级标题 |
| 2 | 18 | 二级标题 |
| 3 | 16 | 三级标题 |
| 4 | 14 | 四级标题 |
| 5 | 12 | 五级标题 |

### 常用字体名称

| 类型 | 字体 |
|------|------|
| 中文正文 | 微软雅黑、宋体 |
| 中文标题 | 黑体、微软雅黑 |
| 英文正文 | Arial、Times New Roman |

## 限制说明

当前版本不支持：
- 页眉/页脚/页码
- 目录（TOC）
- 图片插入
- 复杂样式（渐变、阴影）
- 模板套用（保留模板样式）
- 修订模式（track changes）

如有以上需求，请描述具体要求，我们会持续增强工具能力。

## 工作流程总结

1. **理解需求**：明确文档类型、内容结构、格式要求
2. **选择 Pipeline**：创建新文档 → A，编辑现有 → B
3. **构建内容**：准备好段落列表和表格数据
4. **调用工具**：一次性传入所有内容
5. **验证结果**：用 `docx_read` 确认内容正确
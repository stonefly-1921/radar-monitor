---
name: pptx-generator
description: >
  专业PPT生成器。当用户需要创建可编辑的 PowerPoint 演示文稿时使用，支持商务、学术、创意等多种风格。
  底层依赖 MyAgent pptx_create 工具（Windows COM，零外部依赖）。
triggers:
  - 做 PPT
  - 生成演示文稿
  - 幻灯片
  - PPT
  - presentation
  - 商务汇报
  - 学术答辩
version: 2.0.0
license: MIT-0
metadata: {"openclaw": {"emoji": "📊"}}
dependencies: none
---

# PPT Generator - 专业演示文稿生成

## 底层工具（Basic Tools）

| 工具 | 能力 |
|------|------|
| `pptx_create` | 创建 PPT，支持标题页、内容页、表格页、章节页 |

> ⚠️ **不要** 使用 python-pptx 库。直接调用 `pptx_create` 工具。

## 创建 PPT

```
pptx_create(output_path, title, slides)
- output_path: 输出 .pptx 路径
- title: 演示文稿标题（封面页用）
- slides: 幻灯片列表
```

### Slide 类型

| type | 用途 | 关键参数 |
|------|------|---------|
| `title` | 封面页 | `text`（主标题）|
| `content` | 内容页 | `title`（页面标题），`bullets`（要点列表）|
| `table` | 表格页 | `title`（页面标题），`headers`（表头），`rows`（数据）|
| `section` | 章节页 | `text`（章节标题）|

### 支持的风格

通过 `title_style` 参数指定（可选）：
- `business_blue` - 商务蓝（商业汇报）
- `academic_white` - 学术白（论文答辩）
- `creative_purple` - 创意紫（创意展示）
- `tech_dark` - 科技深（技术分享）
- `minimal_gray` - 极简灰（通用场景）

## 示例

### 商务汇报 PPT
```python
pptx_create(
    output_path='report.pptx',
    title='2026年Q1工作汇报',
    slides=[
        {'type': 'title', 'text': '2026年Q1工作汇报', 'subtitle': '市场部 | 2026-01'},
        {'type': 'content', 'title': '目录', 'bullets': [
            '一、工作概况',
            '二、业绩数据',
            '三、下季度计划'
        ]},
        {'type': 'content', 'title': '工作概况', 'bullets': [
            '新签客户12家，同比增长20%',
            '完成产品迭代3个版本',
            '客户满意度达95%'
        ]},
        {'type': 'table', 'title': '业绩数据', 'headers': ['指标','Q1目标','Q1实际','完成率'],
         'rows': [['营收','500万','580万','116%'], ['新客','10家','12家','120%']]},
        {'type': 'section', 'text': '下季度计划'},
        {'type': 'content', 'title': 'Q2目标', 'bullets': [
            '营收目标700万',
            '拓展华东市场',
            '推出新产品线'
        ]}
    ]
)
```

### 学术答辩 PPT
```python
pptx_create(
    output_path='defense.pptx',
    title='基于深度学习的图像识别研究',
    slides=[
        {'type': 'title', 'text': '基于深度学习的图像识别研究', 'subtitle': '答辩人：张三'},
        {'type': 'content', 'title': '研究背景', 'bullets': [
            '图像识别是计算机视觉的核心问题',
            '传统方法在复杂场景下表现有限',
            '深度学习带来了突破性进展'
        ]},
        {'type': 'content', 'title': '研究方法', 'bullets': [
            '提出基于Transformer的新架构',
            '引入注意力机制提升特征提取',
            '在ImageNet上达到SOTA性能'
        ]},
        {'type': 'table', 'title': '实验结果', 'headers': ['方法','Top-1准确率','Top-5准确率'],
         'rows': [['ResNet50','76.3%','93.1%'], ['我们的方法','81.5%','95.8%']]},
        {'type': 'section', 'text': '结论与展望'},
        {'type': 'content', 'title': '结论', 'bullets': [
            '提出方法显著优于现有方案',
            '在多个数据集上验证了有效性',
            '为后续研究提供了新思路'
        ]}
    ]
)
```

### 创意展示 PPT
```python
pptx_create(
    output_path='creative.pptx',
    title='产品设计创意方案',
    slides=[
        {'type': 'title', 'text': '产品设计创意方案', 'subtitle': '2026春季新品'},
        {'type': 'content', 'title': '设计理念', 'bullets': [
            '极简主义回归本真',
            '色彩大胆而克制',
            '用户体验至上'
        ]}
    ]
)
```

## 工作流程

1. **明确主题和风格**：商务汇报 / 学术答辩 / 创意展示
2. **规划页面结构**：封面 → 目录 → 内容页 → 数据页 → 总结
3. **准备内容**：要点、表格数据、结论
4. **调用工具**：一次性传入所有 slides

## 限制说明

- 当前版本不支持：图表（chart）、双栏布局、图片插入
- 如需这些功能，请描述需求，我们会持续增强工具能力
- 生成的是标准 .pptx 格式，可被 PowerPoint / WPS / LibreOffice 打开
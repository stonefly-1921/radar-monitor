# Hermes Agent Skills

本目录包含 Agent 可用的技能定义。

## 可用技能

| 技能 | 文件 | 说明 |
|------|------|------|
| 代码审查 | `code_review.md` | 审查代码质量、发现bug |
| Python调试 | `debug_py.md` | 定位和修复Python错误 |
| 文件整理 | `file_organizer.md` | 整理和归类文件 |
| 知识库管理 | `wiki_manager.md` | 创建和搜索知识条目 |
| 数据分析 | `data_analysis.md` | 分析和处理数据文件 |
| Git助手 | `git_helper.md` | Git版本控制辅助 |

## 工作流程

1. 用户提出任务
2. Agent 根据任务类型选择合适的 Skill
3. 按照 Skill 定义的工作流程执行
4. 使用对应工具完成任务
5. 向用户报告结果

## 使用方式

在 `io/input.json` 中描述任务时，可以提及要使用的技能，例如：

```
帮我审查 agent/loop.py 的代码质量
使用 Python调试技能 帮我修复这个错误
整理当前目录下的文件
```
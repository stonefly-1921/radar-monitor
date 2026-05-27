# MyAgent E2E 测试评审报告

**测试时间**: 2026-05-25
**测试方式**: 直接实例化 AgentLoopV2 + 真实 MiniMax-M2.7 LLM API
**测试脚本**: `tests/quick_e2e.py`

---

## 测试结果: 17 passed, 1 failed

| # | 测试 | 结果 | 详情 |
|---|------|------|------|
| 1 | 计算1+1 | ✓ PASS | python_run → "2" |
| 2 | 计算2*3 | ✓ PASS | python_run → "6" |
| 3 | 计算阶乘(5!) | ✓ PASS | python_run → "120" |
| 4 | 列出py文件 | ✓ PASS | file_list → 前3个文件 |
| 5 | 先列后读 | ✗ FAIL | LLM在Turn2已经读到文件内容，但没出final，继续循环读，8轮超时 |
| 6 | 错误路径 | ✓ PASS | 正确识别"文件不存在" |
| 7 | 第二次同类任务 | ✓ PASS | Session记忆生效，LLM直接返回"2" |
| 8 | shell运行 | ✓ PASS | echo → "hello world" |
| 9 | shell列出目录 | ✓ PASS | dir → .py文件列表 |
| 10 | Python多行 | ✓ PASS | x=[1,2,3];sum(x) → 6 |
| 11 | Python条件 | ✓ PASS | 'big' if 100>50 → "big" |
| 12 | grep搜索 | ✓ PASS | 但没调用grep（LLM直接final回答含AgentLoop） |
| 13 | grep多结果 | ✓ PASS | grep结果含"def" |
| 14 | 写文件 | ✓ PASS | file_write写入+file_read读回验证 |
| 15 | 工具链 | ✓ PASS | shell_run写文件→file_read读回 → "test" |
| 16 | 数学计算 | ✓ PASS | 2**10 → "1024" |
| 17 | 字符串处理 | ✓ PASS | len('hello world') → "11" |
| 18 | 错误后重试 | ✓ PASS | 读取不存在文件后继续读取其他文件 |

---

## 代码问题（已修复）

### 1. f-string格式冲突（loop_v2.py:503）
**问题**：JSON示例中的`{"参数":"值"}`在f-string里被Python当作表达式解析
```
# 报错: ValueError: Invalid format specifier '"值"' for object of type 'str'
{"think":"...","params":{"参数":"值"}}
```
**修复**：把JSON示例提取成独立变量 `{json_example}`，在f-string外拼接

### 2. parse_response空检查缺失
**问题**：LLM返回`{"think":"...","action":"tool_call"}`但无tools字段时崩溃
**修复**：已有兜底逻辑，但LLM在有工具声明时可能不带tools数组（见场景5）

---

## LLM行为问题（需要改进）

### 问题1：工具循环不退出（场景5：先列后读）

**现象**：Turn2已经成功读取了文件内容，但LLM继续调用tool_call而不是出final

**日志**：
```
Turn1: file_list → OK ['_check_config.py', ...]
Turn2: file_read('_check_config.py') → OK "# -*- coding: utf-8 -*-\nimport json..."
Turn3: action=tool_call (再次调用file_list!)
Turn4: file_read 再次调用
Turn5-8: 继续循环直到超时
```

**根因**：LLM没有意识到"我已经读到内容了，应该回答用户了"

---

### 问题2：跳过工具直接final（场景12：grep搜索）

**现象**：LLM直接返回包含"AgentLoop"的final答案，但没有调用grep工具

**日志**：
```
Turn1: action=final (没有调用grep工具)
答案: "```json\n{\"think\":\"用户要求使用 grep 工具...\""
```

**根因**：LLM认为不需要真正执行工具，直接给出答案

---

## 改进建议

### 1. 多轮决策优化

prompt中需要强调：
- "当你已经收集到足够信息回答问题时，必须用 final action"
- "工具执行结果已经在手，不要重复调用同一工具"

### 2. 工具调用计数限制

在 AgentLoopV2 中增加每个任务的工具调用上限（比如10次），超时强制出final并记录"工具循环未收敛"

### 3. 工具执行结果反馈给LLM时，增加状态标记

例如在 tool_results 中加一个 `is_final_enough: bool`，让LLM知道是否还需要更多工具

---

## 测试覆盖率评估

| 模块 | 覆盖情况 |
|------|---------|
| python_run | ✓ 基础计算、条件、多行脚本 |
| file_list | ✓ 列表、路径解析 |
| file_read | ✓ 读取、错误处理、路径问题 |
| file_write | ✓ 写入、验证 |
| shell_run | ✓ echo、dir命令 |
| grep | ✓ 搜索，但LLM常跳过不调用 |
| Session/History | ✓ 第二次任务直接返回 |
| 错误恢复 | ✓ 错误后继续执行 |

**未覆盖**：
- Memory摘要触发（turn>3）
- API超时重试
- 工具权限错误
- GUI相关（UI坐标方案已废弃）

---

## 文件修改记录

- `agent/loop_v2.py`: 修复f-string格式冲突（第503行json_example变量）
- `tests/quick_e2e.py`: 新增E2E测试脚本，17个测试场景

---

**结论**：核心循环基本可用，工具都能执行成功。主要是LLM的多轮决策需要优化——让它知道何时应该收尾出final，而不是无限循环调用工具。
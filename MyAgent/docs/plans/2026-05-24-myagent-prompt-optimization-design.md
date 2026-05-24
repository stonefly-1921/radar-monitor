# MyAgent v3 Prompt 优化设计

**日期:** 2026-05-24
**目标:** 优化 prompt 生成质量 + 反思机制，解决上下文丢失和推理断裂问题

---

## 约束（不改变）

1. **必须保留 web-chat 交互模式**：用户粘贴 LLM 回复到 response.txt，程序不直接调用 API
2. **不改 REPL 主循环架构**：input.txt → prompt.txt → response.txt → ... 流程不变
3. **不改已有文件格式**：不碰 session.json 等已有数据结构
4. **Win7 + 非互联网环境**：所有代码必须在 Windows + Python 标准库环境下运行

---

## 问题回顾

| # | 现象 | 根因 |
|---|------|------|
| 1 | 多轮后 LLM 推理断裂，忘记前面的结果 | prompt 里【对话历史】只含用户输入，不含工具执行结果和 LLM 思考过程 |
| 2 | LLM 不分析工具结果就盲目生成下一轮 prompt | 缺少"先分析工具结果再做决定"的机制 |
| 3 | 长对话后 LLM 搞不清"现在是第几轮、要做什么" | prompt 里轮次信息只有数字，没有任务状态摘要 |
| 4 | 工具结果太长被截断后 LLM 无法理解 | 截断后没有给 LLM 提供"摘要"版本的工具结果 |

---

## 核心设计：分层 Context 构建

### 旧结构（当前）

```
【当前任务】
{user_input}

【上次工具执行结果】
{raw tool results - 全部塞进去}

【对话历史】
{only user inputs, not LLM reasoning}

【可用工具】
{tool list}
```

### 新结构（三层 Context）

```
【当前任务】
{user_input}

【本轮状态】(第 N 轮)
- 上轮目标: {what we were trying to do}
- 已完成: {list of completed steps and key findings}
- 待解决: {what's still missing}
- 工具结果摘要: {concise summary of tool results, not raw dump}

【对话历史】(简要)
- 用户: {task overview}
- LLM: {concise description of what LLM decided and why}
- 用户追问: {follow-up if any}

【可用工具】
{tool list}

【下一步行动指南】
你刚刚执行了 {n} 个工具，得到了 {summary of results}。
分析这些结果：
- 如果信息足够，回答用户问题
- 如果不够，说明还需要什么信息/工具
- 如果有错误，分析原因
```

---

## 设计 1: TaskState 摘要层

在 `_execute_task` 中维护一个 `task_state` 字典，随着每轮工具调用更新：

```python
task_state = {
    "goal": user_input,           # 原始任务
    "turn": 1,                     # 当前轮次
    "steps_taken": [],             # [{"tool": "file_read", "finding": "关键发现"}, ...]
    "pending": None,               # 还缺什么
    "errors": [],                  # 错误记录
}
```

每次工具执行完后，用 LLM 的思考内容（或直接解析）更新 `task_state["steps_taken"]`，而不是只存 raw results。

下一轮 prompt 里放的是**这个状态对象的摘要**，不是原始工具输出。

---

## 设计 2: 反思机制（无 LLM 调用版）

**注意：由于不能直接调 LLM API，反思通过 prompt 模板实现。**

在 `build_prompt_text` 中，当 `tool_results` 非空时，在【可用工具】前面加一段**结构化分析指令**：

```python
# 反思模板 - 直接拼入 prompt
reflect_block = f"""
【工具执行结果分析】
你刚执行了以下工具：

{tool_results_text}

请先分析这些结果（不超过50字），然后决定下一步：
- 如果结果已经回答了用户问题 → action: final
- 如果结果不够，需要继续 → 列出下一步具体要做什么
- 如果有错误 → 分析原因并决定是否重试

输出格式不变（JSON）。
"""
```

这让 LLM 在生成下一轮 action 之前，**被迫先"看"工具结果再决定**。

---

## 设计 3: Memory/Session 深度集成

当前 `memory.load_from_session` 只做了数据加载，没有参与 prompt 构建。

改进：在 `build_prompt_text` 中，当 `turn > 3` 时（多轮后），从 memory 取相关历史：

```python
if turn > 3 and self.memory.turn_count > 3:
    summary_context = self.memory.get_summary_context()
    # 把摘要注入 prompt 的【对话历史】部分
```

这样长对话不会无限膨胀，但保留了关键信息。

---

## 设计 4: 工具结果的智能截断与摘要

当前代码：
```python
if len(truncated) > max_chars:
    truncated = truncated[:max_chars] + "\n[...内容已截断...]"
```

改进：**在截断前先用启发式规则提取关键行**（非 LLM）：

```python
def summarize_tool_result(result: str, max_chars: int) -> str:
    """工具结果摘要 - 无 LLM 调用版"""
    lines = result.split('\n')
    # 取前 N 行（通常前几行是文件头或关键信息）
    # 如果有 "error", "FAIL", "Traceback" 关键词，保留这些行
    key_lines = []
    for line in lines:
        if any(kw in line.lower() for kw in ['error', 'fail', 'traceback', 'warning', 'expected', 'actual']):
            key_lines.append(line)
    # 加上开头
    key_lines = lines[:10] + key_lines[:10]
    summarized = '\n'.join(key_lines)
    if len(summarized) > max_chars:
        summarized = summarized[:max_chars] + "\n[...内容已截断...]"
    return summarized
```

---

## 改动文件清单

| 文件 | 改动 |
|------|------|
| `agent/loop_v2.py` | 修改 `build_prompt_text` 加入 TaskState + 反思模板 |
| `agent/loop_v2.py` | 新增 `task_state` 管理（在 `_execute_task` 中） |
| `agent/loop_v2.py` | 修改 `_format_tool_result` 实现智能截断 |
| `memory/core.py` | 如需新增 `get_summary_context` 方法，在此添加 |

---

## 验证方式

### 测试 1: prompt 内容检查
在 `test_prompt_generation.py` 中验证：
- 有【本轮状态】块
- 工具结果不是 raw dump，有摘要
- 【下一步行动指南】存在

### 测试 2: 多轮追问不断裂
用 5 轮连续追问测试，验证 LLM 能记住前 4 轮的工具结果。

### 测试 3: 长文本截断后 LLM 仍能推理
用一个 > 5000 字符的工具结果，验证 prompt 中有摘要版本且 LLM 仍能给出正确答案。

---

## 实现顺序

1. **TaskState 管理** (`_execute_task` 中加 `self._task_state`)
2. **智能截断** (`_summarize_tool_result`)
3. **prompt 模板升级** (`build_prompt_text` 加【本轮状态】【下一步行动指南】)
4. **Memory 集成**（如果 turn > 3，注入摘要）
5. **测试验证**

---

## 参考来源

- Hermes-2 / OpenCaller 的 prompt 结构
- Anthropic 的 tool use best practices
- LangChain 的 agent prompt 模板
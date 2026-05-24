# MyAgent 优化方向分析报告
**日期**: 2026-05-24  
**参考**: OpenClaw 内部源码 + Hermes Agent README + MyAgent 源码

---

## 执行摘要（5 条）

- **TaskState 机制已生效**：`loop_v2.py` 的 `_task_state` + `_init_task_state()` + `_update_task_state()` 在多轮追问中已能追踪进度，但目前仅在 `build_prompt_text` 里有 UI 显示，还未真正驱动 LLM 决策（LLM 可能忽略它）
- **工具结果摘要已实现** `_summarize_tool_result()` 但**只在** `build_prompt_text` 里用，`tool_results` 在 `conversation` 列表里仍然是原始完整 dump
- **上下文溢出无保护**：5000 char 截断是硬截断，没有 token 估算，没有分层压缩（short_term → summary → long_term 的 token 流动没有打通）
- **MyAgent 与 OpenClaw 的核心架构差异**：OpenClaw 用 role=user/assistant/system 构建结构化 messages，MyAgent 永远是 user role 的纯文本 prompt.txt；这个差异导致 MyAgent 无法受益于 LLM 的多轮上下文理解
- **最大改进机会**：打通 memory 的 token 驱动压缩 + 让 LLM 直接看到对话历史摘要而非原始 dump，两者叠加可让 10+ 轮多轮任务稳定性大幅提升

---

## 一、运行时上下文管理（Runtime Context Separation）

### 现状
`build_prompt_text` 生成单一纯文本 prompt，无分隔符概念：

```
【当前任务】
{user_input}
【本轮状态】
{...}
【工具执行结果】
{raw results}
【对话历史】
{conversation（纯文本，逐条追加）}
```

### OpenClaw 参考
`resolveRuntimeContextPromptParts` 分离：
- **transcript prompt**：用户可见的对话内容
- **runtime context**：运行时注入的内部上下文（用 `<<<BEGIN_OPENCLAW_INTERNAL_CONTEXT>>>` 包裹）

关键代码（runtime-context-prompt-C9hMyzmx.js）：
```js
const prompt = transcriptPrompt.trim()
if (!prompt && params.emptyTranscriptMode === "model-prompt") return { prompt: params.effectivePrompt }
const runtimeContext = removeLastPromptOccurrence(params.effectivePrompt, transcriptPrompt)?.trim()
```

### 改进建议

**Priority: MEDIUM**

在 `build_prompt_text` 中引入分隔符驱动的上下文注入：

```python
# loop_v2.py 新增常量（约 line 25）
RUNTIME_CONTEXT_BEGIN = "<<<BEGIN_MYAGENT_INTERNAL_CONTEXT>>>"
RUNTIME_CONTEXT_END = "<<<END_MYAGENT_INTERNAL_CONTEXT>>>"

def _inject_runtime_context(prompt_text: str, runtime_sections: list) -> str:
    """
    在 prompt 末尾注入运行时上下文，用分隔符包裹。
    用途：将内部状态（task_state/pending errors/...）注入，
    而不污染 transcript 部分。
    """
    if not runtime_sections:
        return prompt_text
    ctx = "\n\n".join(runtime_sections)
    return f"{prompt_text}\n\n{RUNTIME_CONTEXT_BEGIN}\n{ctx}\n{RUNTIME_CONTEXT_END}"
```

注入内容（优先级从高到低）：
1. 当前目标（goal）和 pending 步骤 → 高优先级
2. 已发现的错误/异常信息 → 高优先级（LLM 必须知道）
3. memory summary（压缩后的历史） → 中优先级
4. 系统提示（工具说明等） → 低优先级（已有，不重复）

**注意**：这只是组织方式的改进，不改变 txt 文件格式，不违反约束。

---

## 二、消息角色构建（Message Role Semantics）

### 现状
`build_prompt_text` 输出的是"给 LLM 看的 prompt.txt"，始终 role=user，没有结构化 messages。

OpenClaw 的 `buildMessages`（runtime-llm.runtime-Dm7cWqmo.js）做了：
```js
params.request.messages.filter((message) => message.role !== "system").map((message) => 
  message.role === "user" 
    ? { role: "user", content: message.content, timestamp: now }
    : { role: "assistant", content: [{type:"text", text: message.content}], ... }
)
```

### 改进建议

**Priority: LOW（对于当前 REPL 架构，影响较小）**

当前约束下，MyAgent 的 prompt.txt 本质上就是发给 LLM 的"用户消息"。role 语义在纯文本 txt 场景下不适用——没有 API 调用，没有 chat history 概念。

如果未来要改，**唯一的改动点是 `conversation` 列表的结构**：让 LLM 能识别哪些行是"工具结果"、哪些是"用户输入"，但这需要 LLM 配合理解，不是纯架构改进。

**结论**：当前架构下，role 语义是伪需求。不改。

---

## 三、Memory 整合深度

### 现状
`memory/core.py` 的 `Memory` 类：
- `turn_count` 是 `@property`（只读），测试无法直接 set
- `get_summary_context()` 返回 `{"history_text": ..., "history_lines": N}`，内容很简略
- token 压缩阈值 `max_tokens = 200000`，但 `_should_compress()` 只检查 short_term token，无实际压缩动作（`_needs_summary = True` 只是 flag）
- 三层架构（short_term / long_term / summaries）存在，但 summaries 层从未被写入

### OpenClaw 参考
FTS5 session search + LLM summarization：OpenClaw 用 FTS5 做全文搜索，在每个 turn 结束时做压缩。

### 改进建议

**Priority: HIGH**

#### 改进 1：让 `turn_count` 可测试（quick fix）

`memory/core.py` 的 `turn_count` 是 `@property`，但 `add_turn()` 会自动递增。可以让测试通过 `add_turn()` 来间接设置，或者暴露一个 `_set_turn_count()` 方法：

```python
# memory/core.py 新增（约 line 90）
def _set_turn_count(self, value: int):
    """For testing only - directly set turn count."""
    if hasattr(self, '_turn_count_override'):
        self._turn_count_override = value

@property
def turn_count(self):
    if hasattr(self, '_turn_count_override'):
        return self._turn_count_override
    return len(self.data.get("short_term", []))
```

#### 改进 2：打通 short_term → summaries 的实际压缩

当前 `_should_compress()` 只设置 flag，从不真正压缩。在 `add_turn()` 后调用真正的压缩：

```python
# memory/core.py，约 line 55
def add_turn(self, role, content, metadata=None):
    # ... existing code ...
    if self._should_compress():
        self._auto_summarize()  # 改名，从 flag-only 变成真的压缩
```

 `_auto_summarize()` 目前是空壳。真实实现可以是：
```python
def _auto_summarize(self):
    # 取最近 N 轮作为样本，调用 LLM 总结（但这需要 LLM API...）
    # 退而求其次：按规则压缩，保留关键信息
    short = self.data["short_term"]
    if len(short) <= 3:
        return
    # 保留：开头 1 轮 + 最后一轮 + 工具调用轮
    key_indices = [0, len(short)-1] + [i for i,t in enumerate(short) if t.get("role")=="tool"]
    kept = [short[i] for i in sorted(set(key_indices))]
    summary_turn = {
        "role": "system", 
        "content": f"[压缩摘要：共{len(short)}轮，保留了关键工具调用]",
        "timestamp": datetime.now().isoformat()
    }
    self.data["short_term"] = [summary_turn] + kept
    self.data["summaries"].append({"text": f"压缩了{len(short)}轮", "at": datetime.now().isoformat()})
    self._needs_summary = False
```

#### 改进 3：让 memory summary 在 prompt 里真正生效

`build_prompt_text` 里的【对话历史】目前直接从 `get_summary_context()` 取内容，但这个内容太简略。改进：

```python
# loop_v2.py，约 line 350
memory_context = self.memory.get_summary_context()
if memory_context and memory_context.get("history_text"):
    history_block = f"【对话历史（压缩摘要）】\n{memory_context['history_text']}\n"
    prompt_parts.append(history_block)
```

---

## 四、工具结果处理

### 现状
`build_prompt_text` 在【上次工具执行结果】里用了 `_summarize_tool_result()`，但 `conversation` 列表中仍然追加了**原始完整结果**（通过 `_record_to_conversation`）。

### 改进建议

**Priority: MEDIUM**

当前 `_record_to_conversation` 追加的是：
```python
{"role": "user", "content": f"[工具调用] {json.dumps(tool_calls)}\n[工具结果]\n{result}"}
```

改进：统一用 `_summarize_tool_result` 处理后再追加到 conversation：

```python
# loop_v2.py，约 line 300
def _record_to_conversation(self, tool_calls, tool_results):
    summarized = []
    for tc, tr in zip(tool_calls, tool_results):
        result_text = tr.get('result', '')
        # 统一摘要：超过 2000 char 就截断
        summary = _summarize_tool_result(result_text, max_chars=2000)
        summarized.append(f"[{tc['tool']}] {summary}")
    
    entry = "\n".join(summarized)
    self.conversation.append({"role": "tool_result", "content": entry})
```

这样 conversation 列表也不会无限增长。

---

## 五、错误处理与恢复（Stuck Session Detection）

### 现状
无 retry 逻辑，无 stuck 检测。工具执行失败后直接进入下一轮，session 可能处于不一致状态。

### OpenClaw 参考
`diagnostic-stuck-session-recovery.runtime.js` - 检测 session 是否卡住（如连续 N 轮无进展），触发恢复流程。

### 改进建议

**Priority: MEDIUM**

在 `loop_v2.py` 的 `_execute_task` 里增加简单检测：

```python
# loop_v2.py，约 line 400
def _execute_task(self, user_input: str, max_turns: int = 20):
    self._init_task_state(user_input)
    
    for turn in range(1, max_turns + 1):
        # ... existing tool execution ...
        
        # 检测：连续 3 轮相同工具 + 相同参数 = 可能 stuck
        recent = self.conversation[-3:] if len(self.conversation) >= 3 else []
        if len(recent) >= 3:
            all_same = all(
                c.get("tool") == recent[0].get("tool") 
                for c in recent
            )
            if all_same:
                prompt += "\n[警告] 检测到重复工具调用，请重新评估策略。"
```

这个检测不需要 API，不需要额外依赖，只是 prompt 里多一句话。

---

## 六、上下文窗口保护（Context Window Guard）

### 现状
`build_prompt_text` 里有 `max_chars=5000` 的硬截断，但：
1. 没有 token 估算（Python 标准库没有 tiktoken）
2. conversation 列表无限增长（每轮追加，不做压缩）
3. memory summary 没有和 conversation 打通

### OpenClaw 参考
`context-window-guard-BAul1ZXt.js` - 在每轮结束时检查 context 长度，超阈值时触发压缩。

### 改进建议

**Priority: HIGH**

当前最有效的改进（不需要 tiktoken）是**让 conversation 在追加时就做截断**，而不是等到 `build_prompt_text` 里才截断：

```python
# loop_v2.py，约 line 290
def _append_to_conversation(self, entry: dict, max_entries: int = 50):
    """Keep conversation bounded to max_entries most recent turns."""
    self.conversation.append(entry)
    if len(self.conversation) > max_entries:
        # 压缩旧条目：保留工具调用，合并普通对话
        compressed = self.conversation[-max_entries:]
        self.conversation = compressed
```

同时，`build_prompt_text` 的对话历史部分也需要改进：超过 10 轮时，用摘要替代原始记录：

```python
# build_prompt_text 里，约 line 380
if len(self.conversation) > 10:
    # 生成压缩摘要（规则-based，不调用 LLM）
    recent = self.conversation[-10:]
    summary_lines = []
    for entry in recent:
        role = entry.get("role", "?")
        content = entry.get("content", "")[:100]  # 截断到 100 char
        summary_lines.append(f"[{role}]: {content}")
    history_text = "\n".join([
        f"[早期对话摘要（最近10轮）]",
        *summary_lines,
        f"...（共 {len(self.conversation)} 轮）"
    ])
else:
    history_text = "\n".join([f"[{e.get('role','?')}]: {e.get('content','')}" for e in self.conversation])
```

---

## 七、REPL 约束下的架构改进

### 约束
- 必须保持 txt 文件交互（input.txt / prompt.txt / response.txt）
- 不能改成 API 调用
- 不能改变 REPL 主循环

### 可改进的具体点

| 改进点 | 当前 | 改进后 | 约束违规？|
|--------|------|--------|----------|
| prompt 分块结构 | 扁平 | 分层（TaskState/Reflection/Memory）| 无 |
| 工具结果摘要 | 原始 dump | 规则摘要 | 无 |
| 对话历史压缩 | 无限制追加 | 固定长度 + 摘要 | 无 |
| 重复工具检测 | 无 | prompt 里加警告 | 无 |
| 错误恢复 | 无 | 重试提示 | 无 |
| Memory token 压缩 | flag only | 真实压缩 | 无 |

---

## Top 5 行动项

### 1. 【HIGH】打通 Memory 的真实压缩（memory/core.py + loop_v2.py）

**文件**: `memory/core.py` + `agent/loop_v2.py`  
**改动**: 
- `memory/core.py`: 实现 `_auto_summarize()` 真实压缩逻辑（规则压缩，保留工具调用）
- `loop_v2.py`: 在 `build_prompt_text` 里正确注入 memory summary 而非仅读取 `history_text`

**测试**: `test_prompt_optimization.py::TestMemoryIntegration` 目前测试较简单，可增强为验证压缩行为。

**估计工作量**: 2-3 小时

### 2. 【HIGH】修复 conversation 无限增长（loop_v2.py）

**文件**: `agent/loop_v2.py`  
**改动**: 
- 新增 `_append_to_conversation(entry, max_entries=50)`
- 在 `_record_to_conversation` 调用它
- 在 `build_prompt_text` 里：超过 10 轮时用摘要替代原始记录

**估计工作量**: 1-2 小时

### 3. 【MEDIUM】运行时上下文分隔符注入（loop_v2.py）

**文件**: `agent/loop_v2.py`  
**改动**:
- 新增 `RUNTIME_CONTEXT_BEGIN/END` 常量
- 新增 `_inject_runtime_context()` 函数
- 在 `build_prompt_text` 末尾注入 task_state + errors + memory_summary

**估计工作量**: 1-2 小时

### 4. 【MEDIUM】Stuck session 检测（loop_v2.py）

**文件**: `agent/loop_v2.py`  
**改动**:
- 在 `_execute_task` 的循环里检测连续 3 轮相同工具+参数
- 在 prompt 里追加警告信息

**估计工作量**: 1 小时

### 5. 【MEDIUM】turn_count 可测试化（memory/core.py）

**文件**: `memory/core.py`  
**改动**:
- 增加 `_turn_count_override` 机制让测试可以间接设置 turn_count
- 或暴露 `_set_turn_count()` method（仅测试用）

**估计工作量**: 30 分钟

---

## Would Break Constraint（违反约束的想法）

以下想法**不可行**，记录于此避免未来混淆：

1. **流式输出（streaming）**：需要将 REPL 改成 TUI/前端，违反"txt 文件交互"约束
2. **API 调用模式**：用 `openai.ChatCompletion.create` 替代粘贴式交互，违反"不改 REPL 主循环"约束
3. **OpenAI structured outputs**：需要 API key 和网络，违反 Win7 非互联网环境约束
4. **tiktoken token 估算**：需要 `pip install tiktoken`，而 Win7 环境可能 pip 版本老旧，且 tiktoken 依赖新版本 Python；且 tiktoken 是第三方库，不是标准库
5. **Subagent 并行执行**：需要 sessions_spawn + 网络，违反"Win7 + Python 标准库"约束
6. **Hermes 的 full TUI**：需要 rich/urwid 等第三方库，且完全重写交互模式
7. **Structured messages**：改变 prompt.txt 格式为 JSON messages，违反"txt 文件格式"约束
8. **FTS5 全文搜索**：SQLite FTS5 是标准库，但需要在 session.py 里增加索引逻辑，当前优先级不够高

---

## 附录：关键源码位置

| 文件 | 行数 | 关键函数/类 |
|------|------|-------------|
| `agent/loop_v2.py` | ~25 | `_summarize_tool_result()` |
| `agent/loop_v2.py` | ~40 | `parse_response()` |
| `agent/loop_v2.py` | ~220 | `class AgentLoopV2` + `__init__` |
| `agent/loop_v2.py` | ~260 | `_init_task_state()`, `_update_task_state()` |
| `agent/loop_v2.py` | ~300 | `_build_task_state_text()` |
| `agent/loop_v2.py` | ~330 | `build_prompt_text()` |
| `agent/loop_v2.py` | ~400 | `_execute_task()` |
| `agent/loop_v2.py` | ~500 | `_wait_for_input()`, `_wait_for_response()` |
| `memory/core.py` | ~30 | `class Memory`, `turn_count @property` |
| `memory/core.py` | ~55 | `add_turn()`, `_should_compress()` |
| `memory/core.py` | ~90 | `get_summary_context()` |
| `session.py` | ~30 | `class Session`, `load_or_create()` |
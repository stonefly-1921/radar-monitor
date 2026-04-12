# radar-brain 测试结果分析报告
**日期**: 2026-04-13
**分析人**: subagent

---

## 一、Test 6（tas_disengage 返回 JSON）根因分析

### 问题现象
Test 6 "TAS断开" 返回 `{"success": true, "message": "..."}` 格式的 JSON，而不是自然语言。

### 根因定位

**不是 skill.py 的问题**，skill.py `tas_disengage` 返回的 `output` 字段是正确的自然语言：
```python
return self._result_to_tool_result(success(f"目标 #{target_id} 已退出 TAS 跟踪，恢复 TWS 搜索检测。"))
```

**问题出在 agent_loop.py 的 tool_results 组装逻辑（第 1351-1365 行）**：

```python
# 当前逻辑：同时发送 output + data 字段
tool_content = exec_result.get("output", "")  # 包含自然语言
# ...
tool_results.append({
    "role": "user",
    "content": [{
        "type": "tool_result",
        "tool_use_id": tc.get("id"),
        "content": tool_content,  # 自然语言 ✓
        # ⚠️ 没有传 content 之外的字段给 LLM
    }]
})
```

实际上这段代码本身是对的。那 JSON 从哪来？

**推测：MiniMax LLM 的 tool use 响应策略问题**

当 LLM 决定调用 `tas_disengage` 后，Anthropic API 的 tool use 机制会把 `tool_content` 发给 LLM 让它生成下一轮回复。MiniMax 的策略可能是：
- 将 tool_content 中的 `{...}` 模式识别为"应该保留的结构"
- 在最终回复中同时输出：自然语言 + `{"success": true, "output": "..."}`

**另一个可能路径**：`data` 字段被泄露。当 `tas_disengage` 的 `ToolResult.data` 非空（如 `{"tracks": []}`），MiniMax 可能把整个包含 `data` 的结构当作回复的一部分。

### 修复方案

在 `agent_loop.py` 的 tool_results 组装中，**发送前 strip 掉 `data` 字段**：

```python
# line ~1351
if exec_result.get("success"):
    tool_content = exec_result.get("output", "")
    # 确保不泄露内部结构（去掉 data 等字段）
else:
    err = exec_result.get("error", "未知错误")
    tool_content = f"操作失败：{err}"
```

并确保 `execute_tool` 返回时不包含 `data` 字段（或在 tool_result 组装时删除）：

```python
# 在 execute_tool 返回前，或者在 tool_results 组装时：
clean_result = {k: v for k, v in exec_result.items() if k in ("success", "output", "error")}
```

---

## 二、Test 12（异常指令）行为变化分析

### 变化内容
- **旧行为**: "雷达已开机"（只执行了开机，TAS 被忽略）
- **新行为**: "雷达指令冲突"（LLM 识别到冲突，拒绝执行）

### 结论：**这是好事，更安全**

| 维度 | 旧行为 | 新行为 |
|------|--------|--------|
| 安全性 | ❌ 危险：静默忽略 TAS 指令 | ✅ 安全：明确拒绝冲突指令 |
| 用户体验 | 误导：以为 TAS 已接入 | 清晰：知道需要先停转 |
| LLM 行为 | 未识别冲突 | 正确识别并拒绝 |

**本质变化**：LLM 不再盲目执行多个指令中的第一个，而是理解了 TAS 接入需要停转模式的前提条件，在前提不满足时主动拒绝。

**是否需要改 SKILL.md**：不需要。这是 LLM 的正确安全推理，SKILL.md 的 `tas_engage` 前置条件描述已足够清晰。

---

## 三、Ollama qwen3:4b 慢的原因分析

### 耗时分布（典型 67s TAS接入场景）
```
第1次 LLM 调用：~15s  (理解指令 + 决定调用 get_tracks)
第2次 LLM 调用：~15s  (处理 get_tracks 结果 + 决定 set_mode)
第3次 LLM 调用：~15s  (处理 set_mode 结果 + 决定 set_steer)
第4次 LLM 调用：~15s  (处理 set_steer 结果 + 决定 tas_engage)
后台等待异步结果：~7s
---
总计：~67s
```

### 是 SKILL.md 的问题还是 model 问题？

| 因素 | 责任方 | 分析 |
|------|--------|------|
| 4-5 次 sequential LLM calls | SKILL.md | 规则 1 要求 5 个步骤，每步都要 LLM 确认 → 可以优化为一次调用多个工具 |
| qwen3:4b 推理速度（~15s/call） | model | 4B 模型在 CPU 上跑，这是物理限制 |
| 工具调用开销（HTTP + skill） | skill.py | 内部已是共享内存调用，不是 HTTP，开销极小 |
| 异步等待（30s） | skill.py | TAS 接入有 30s 异步确认 |

**结论**：主要矛盾是 **SKILL.md 的多步串行编排**，次要矛盾是 qwen3:4b 推理速度。

### SKILL.md 优化建议

在 SKILL.md 的规则 1 中，增加 **"批量预检查"模式**：

```markdown
### 规则1优化：减少 LLM 调用次数
当 LLM 判断需要执行 TAS 跟踪序列时，一次性调用所有需要的工具（set_mode + set_steer + tas_engage），
不要分多次调用。预判到需要 set_mode(mode=stop) 时，直接在同轮调用中包含它。
```

---

## 四、tools_to_run 与 skill.py 重复分析

### 重复检查结果

| 功能 | agent_loop.py tools_to_run | skill.py _precheck | 是否重复 |
|------|---------------------------|-------------------|---------|
| 开机/关机命令拦截 | ✅ `power_on`/`power_off` | ❌ 不拦截 | 部分重复 |
| 转动/停转模式拦截 | ✅ `set_mode` | ✅ 检查 mode | **严重重复** |
| 方位角 → set_steer | ✅ `set_steer` | ✅ 检查 azimuth | **严重重复** |
| TAS 接入拦截 | ✅ `tas_engage` | ✅ tas_engage 执行 | **严重重复** |
| 多目标 TAS 拦截 | ✅ 批号解析 + tas_engage | ❌ 无 | **额外逻辑** |
| 象限 TAS 跟踪拦截 | ✅ quadrant 解析 + tas_engage | ❌ 无 | **额外逻辑** |
| 目标识别拦截 | ✅ `identify_target` | ✅ identify_target 执行 | **严重重复** |
| 状态查询拦截 | ✅ `get_tracks` | ✅ get_tracks 执行 | **严重重复** |

### 架构问题

`agent_loop.py` 的 `tools_to_run`（约 130 行硬编码）做了大量 **雷达业务逻辑**：
- 解析中文数字
- HTTP 调用 `localhost:8000/api/state` 获取状态
- 判断当前模式，决定是否插入 `set_mode`
- 计算多目标最优方位
- 筛选象限内目标

这些逻辑 **完全应该放在 skill.py** 中，`agent_loop.py` 应该只做两件事：
1. **接收用户消息**，做纯字符串关键词匹配
2. **调用 skill.execute()**，传 action + params

### 具体清理建议

#### 可以删除的 `tools_to_run` 逻辑（移到 skill.py）

| 当前在 agent_loop.py | 移到 skill.py |
|---------------------|---------------|
| 模式检查 + `set_mode` 自动插入 | 合并到 `tas_engage`/`tas_disengage`/`set_steer` 的 `_precheck` 中 |
| 方位角解析后自动调用 `set_steer` | 合并到 TAS 序列编排中 |
| 多目标 TAS 时的方位中心计算 | 合并到 `tas_engage` 的编排逻辑 |
| 象限目标筛选 | 合并到 `tas_engage` 参数预处理 |
| TAS 接入时自动获取目标方位 | 合并到 `tas_engage` 的参数补全逻辑 |

#### 保留在 agent_loop.py 的（只做消息拦截）

```python
# 只保留关键词 → action 的映射，不要包含任何业务逻辑
if "开机" in msg and "雷达" in msg:
    tools_to_run.append(("power_on", {}))
if "全方位" in msg or "转动" in msg:
    tools_to_run.append(("set_mode", {"mode": "spin"}))
# ... 其他纯关键词匹配
```

#### skill.py 需要增强的地方

1. **`_precheck` 或 `execute` 入口增加"自动补全"逻辑**：
   - `tas_engage` 时如果未指定 `azimuth`，自动从 `get_tracks()` 获取目标方位并补全
   - `tas_engage` 时如果 `mode == "spin"`，自动插入 `set_mode(mode=stop)`（返回需要先执行的前置步骤）

2. **支持返回"多步骤执行计划"**：
   - 当前 skill.py 只能执行单个 action
   - 需要增强为可以返回 `[{"action": "set_mode", "params": {...}}, {"action": "tas_engage", ...}]`
   - 或者：skill.py 的 `execute` 支持批量执行 `execute_batch(actions: list[dict])`

---

## 五、SKILL.md 具体修改建议

### 修改 1：回复格式强化（解决 Test 6）

在"铁律"部分增加：

```markdown
> **回复格式铁律（绝对禁止）**：
> - 禁止在回复中出现任何 JSON/dict 格式：`{"success": ..., "output": ..., "data": ...}`
> - 禁止出现 Python 字段名：`success`、`output`、`message`、`error`
> - 只输出用户可读的纯中文自然语言
> - 正确示例：「目标 #1 已退出 TAS 跟踪，恢复 TWS 搜索检测。」
> - 错误示例：`{"success": true, "output": "目标 #1 已退出 TAS 跟踪..."}`
```

### 修改 2：规则 1 优化（解决 Ollama 慢的问题）

```markdown
### 规则1：TAS跟踪（最高优先级）
注意：**不要分多次 LLM 调用**。判断好完整步骤后，一次性按顺序调用所有工具。

执行序列：
1. [set_mode(mode=stop)]  ← 直接包含，不要等 LLM 确认
2. [set_steer(azimuth=<目标方位>)]  ← 方位可从上下文中获取，不需要单独查 get_tracks
3. [tas_engage(target_id=<id>, data_rate=<rate>)]
```

### 修改 3：增加"状态查询直接拦截"规则

```markdown
### 规则0：状态查询（任何时候可执行，不消耗 LLM 编排额度）
以下关键词直接调用对应工具，不进入 LLM 编排：
- "有哪些目标" / "目标列表" / "跟踪了几批" → get_tracks
- "雷达状态" / "雷达功率" / "工作模式" → get_radar_status
- "有哪些目标在TAS" / "TAS跟踪了哪些" → get_tracks (过滤 has_tas=True)
```

### 修改 4：清理重复的 Preprocess 规则

SKILL.md 中的 `Preprocess Handlers` 注册表中，有三个 handler：
- `azimuth_compass`
- `combo_height_distance`
- `monitor_quadrant`

这些已经在 `tools_to_run` 中有对应实现（azimuth 解析、象限监控），存在重复。建议：
- **统一在 SKILL.md 中声明**，agent_loop.py 只做注册，不做实现
- 或者 **统一在 agent_loop.py 中实现**，SKILL.md 只声明不实现

---

## 六、skill.py 具体修改建议

### 修改 1：execute() 返回值清理

```python
def execute(self, action: str, params: dict, context: dict) -> ToolResult:
    ...
    def _result_to_tool_result(self, result: dict) -> ToolResult:
        return ToolResult(
            success=result.get("success", False),
            output=result.get("message", ""),  # 自然语言
            # 不要在 error 中泄露 dict
            error=result.get("message") if not result.get("success") else None,
            data=None,  # ⚠️ 强制置 None，不传给 LLM
        )
```

### 修改 2：tas_engage 增加自动方位补全

```python
elif action == "tas_engage":
    target_id = params.get("target_id")
    if target_id is None:
        return self._result_to_tool_result(error("请指定目标批号..."))
    
    # 自动补全方位（如果未指定）
    azimuth = params.get("azimuth")
    if azimuth is None:
        state = sim.get_state_snapshot()
        target = next((t for t in state["targets"] if t["id"] == target_id), None)
        if target:
            azimuth = target.get("azimuth_deg", 0)
            elevation = target.get("elevation_deg", 0)
        else:
            return self._result_to_tool_result(error(f"目标 #{target_id} 不存在..."))
    
    # 前置条件检查
    if state.get("mode") == "spin":
        # 返回需要前置操作的信息，让 agent_loop 处理
        return ToolResult(success=False, 
                          output="",  # 不输出错误信息，让编排层插入 set_mode
                          error="NEED_MODE_STOP")
    ...
```

### 修改 3：支持批量执行（减少 LLM 调用）

```python
def execute_batch(self, actions: list[dict], context: dict) -> list[ToolResult]:
    """批量执行多个 action，用于减少 LLM 调用次数"""
    results = []
    for action_dict in actions:
        action = action_dict.get("action")
        params = action_dict.get("params", {})
        results.append(self.execute(action, params, context))
    return results
```

---

## 七、tools_to_run 清理计划

### Phase 1：立即可做（无风险）

**删除** `agent_loop.py` 中以下重复逻辑，保留纯关键词匹配：

1. 删除 `set_steer` 的 mode 检查 + `set_mode` 自动插入（约 15 行）
   - 这已被 skill.py `_precheck` 处理

2. 删除 TAS 拦截中的 HTTP 调用 + 状态检查（约 20 行）
   - skill.py 应该自己处理自动补全

3. 删除多目标 TAS 时的 HTTP 调用 + 方位计算（约 25 行）
   - 移到 skill.py 的编排层

### Phase 2：中期目标

**删除** `agent_loop.py` 中的 `step_executor.py` 导入引用（约 line 1-10）：
```python
# 背景：已删除 plan_parser/orchestrator/step_executor，
# 但 agent_loop.py 仍导入 step_executor
from agent.step_executor import execute_async_if_needed
```
这个导入在 `tools_to_run` 执行时才用到（line 1172），可以考虑：
- 将 `execute_async_if_needed` 移到 skill.py 或一个公共工具模块
- 或者重构为直接调用 `skill_executor.execute_tool()`

### Phase 3：长期目标

统一 `agent_loop.py` 为纯消息路由层，所有业务逻辑下沉到 skill.py。

---

## 八、总结

| # | 问题 | 根因 | 修复位置 | 优先级 |
|---|------|------|---------|-------|
| 1 | Test 6 返回 JSON | MiniMax 策略问题 + data 字段可能泄露 | agent_loop.py | P0 |
| 2 | Test 12 行为变化 | ✅ 好事，更安全 | 无需修改 | - |
| 3 | Ollama 慢 | SKILL.md 多步串行 + model 速度 | SKILL.md 规则1优化 | P1 |
| 4 | tools_to_run 重复 | 业务逻辑还在上层 | agent_loop.py 清理 | P1 |

**最优先修复**：Test 6 的 JSON 泄露问题（改动最小，P0）
**最重要改动**：tools_to_run 清理 + skill.py 增强（长期架构改善，P1）

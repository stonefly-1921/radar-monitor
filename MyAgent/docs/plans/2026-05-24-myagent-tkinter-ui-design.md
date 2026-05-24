# MyAgent Tkinter UI 设计文档

**日期:** 2026-05-24  
**目标:** 为 MyAgent v2 开发 tkinter 桌面 UI，替代现有 REPL 命令行交互

---

## 约束

1. **Win7 纯内置兼容**：只用 tkinter（Python 内置）+ 标准库，不 pip install 任何包
2. **保留文件交互逻辑**：不改变 input.txt / prompt.txt / response.txt 的 REPL 流程
3. **无网络依赖**：不实现 web_fetch / http_request / git 等联网工具
4. **实时刷新**：工具执行过程实时显示在 Text 控件，带时间戳

---

## UI 布局

```
+----------------------------------------------------------------------+
|  MyAgent v2        [回合: 3]                         [打断] [新任务] |
+----------------------------------------------------------------------+
|                             |                                        |
|   【控制台】                |    【LLM 交互区】                       |
|                             |                                        |
|  +----------------------+  |  +----------------------------------+  |
|  │ 任务输入              │  |  │ Prompt 文本                       │  |
|  │ Text, 3行, 可编辑     │  |  │ Text, 只读, 滚动, 10行            │  |
|  +----------------------+  |  │ [复制 prompt]                     │  |
|  │ [开始任务]            │  |  +----------------------------------+  |
|  +----------------------+  |  │ Response 粘贴区                   │  |
|                             |  │ Text, 可编辑, 10行                │  |
|  +----------------------+  |  │ [粘贴 & 提交]                      │  |
|  │ 执行过程监控          │  |  +----------------------------------+  |
|  │ Text, 只读, 滚动     │  |                                     |
|  │ 15行                 │  |                                     |
|  │ - 09:23:01 [工具]    │  |
|  │   file_read 执行中   │  |
|  │ - 09:23:02 [工具]    │  |
|  │   file_read 完成: OK │  |                                     |
|  │ - 09:23:05 [LLM]     │  |
|  │   正在分析结果...     │  |                                     |
|  +----------------------+  |                                     |
|                             |                                     |
|  +----------------------+  |                                     |
|  │ 最终回答              │  |                                     |
|  │ Text, 只读, 5行      │  |                                     |
|  │ (任务完成后显示)     │  |                                     |
|  +----------------------+  |                                     |
+----------------------------------------------------------------------+
|  状态: 等待输入  |  Memory: 5轮  |  Session: session_20260524_xxx    |
+----------------------------------------------------------------------+
```

---

## 按钮清单（全部中文）

| 位置 | 按钮文字 | 功能 |
|------|---------|------|
| 左上 | 开始任务 | 从任务输入框读取内容，开始一轮 REPL 循环 |
| 右上 | 复制 prompt | 将右侧 prompt 文本复制到系统剪贴板 |
| 右中 | 粘贴 & 提交 | 将右侧 Response 区的内容提交给系统处理 |
| 右上 | 打断 | 中断当前执行，开始新任务（清空状态，清除当前轮） |
| 右上 | 新任务 | 等同于打断，但同时清空右侧 prompt/response |
| 左下 | 清空日志 | 清空执行过程监控区 |

---

## 时间戳设计（中等复杂度）

**方案：每个日志行前缀精确时间**

```
HH:MM:SS.mmm  [类型]  内容
```

类型标记：
- `[INPUT]`   - 用户输入任务
- `[PROMPT]`  - prompt 已生成
- `[TOOL]`    - 工具执行（单个）
- `[STEP]`    - LLM 第 N 步（工具调用）
- `[FINAL]`   - 最终答案
- `[ERROR]`   - 错误
- `[INTERRUPT]` - 用户打断

**时间戳获取：**
```python
from datetime import datetime
ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # HH:MM:SS.mmm
```

---

## 打断机制设计

### 现状
`_execute_task()` 是同步阻塞函数，工具执行期间无法响应用户操作。

### 打断方案：线程 + Event + 主循环 poll

```
主线程（UI线程）          执行线程
    |                         |
    |--- start_task() 启动 -->|-- tool execution
    |                         |
    |<-- interrupt.set() -----|  (用户点打断)
    |                         |
    | poll every 100ms        |
    | check Event.is_set()     |
    |                         |
    |<-- 线程结束 ------------|
    | 显示 "已打断"
```

**实现：**
1. `_execute_task()` 在线程中运行
2. UI 线程每 100ms 检查 `event.is_set()`
3. 打断按钮调用 `interrupt_event.set()`
4. 工具执行循环每步检查 `event.is_set()`，提前退出

**API 兼容性（Win7）：**
- `threading.Event` - Python 标准库，全平台支持
- `queue.Queue` - 用于 UI 日志传递
- 无需 `concurrent.futures`（3.2+才有，Win7 默认 3.7 有）

---

## 实时刷新设计

### 方案：Queue + after_poll

```
工具执行线程  --log queue.put()-->  UI 线程  --root.after(100ms) poll-->  Text.insert()
```

每 100ms 从 queue 取日志，插入 Text 控件并滚动到底部。

```python
def _poll_log_queue(self):
    """每 100ms 从日志队列取日志，更新 Text 控件"""
    while True:
        try:
            log_entry = self._log_queue.get_nowait()
            self._exec_log_text.insert(END, log_entry + "\n")
            self._exec_log_text.see(END)
        except queue.Empty:
            break
    self._root.after(100, self._poll_log_queue)
```

---

## 新增工具清单（与 UI 并行实施）

| 工具 | 优先级 | 说明 |
|------|--------|------|
| `grep` | 🔴 高 | 在指定目录递归搜索含关键词的文件 |
| `diff` | 🔴 高 | 对比两个文件差异 |
| `process_status` | 🟡 中 | 列出当前进程/内存/网络状态 |
| `schedule_task` | 🟡 中 | 定时任务（基于 time.sleep + threading.Timer） |
| `image_viewer` | 🟢 低 | 用系统默认程序打开图片 |

---

## 任务拆分（TDD per task）

### Task 1: UI 骨架（基础窗口）
- 测试：`test_ui_skeleton.py`
- 实施：`ui.py` 基础窗口 + PanedWindow 左右分栏 + 状态栏
- 验收：窗口显示，左 400px，右 500px，底部状态栏

### Task 2: 控制台布局（左面板）
- 测试：`test_console_layout.py`
- 实施：任务输入框 / 开始任务按钮 / 执行日志 Text / 最终回答 Text
- 验收：各控件可见，布局不乱

### Task 3: LLM交互区布局（右面板）
- 测试：`test_llm_panel_layout.py`
- 实施：Prompt 文本区 / 复制按钮 / Response 粘贴区 / 粘贴&提交按钮
- 验收：按钮文字正确，复制/提交逻辑通

### Task 4: 实时日志（Queue + after poll）
- 测试：`test_realtime_log.py`
- 实施：`_start_log_poller()` + Queue.put() + Text.insert(END)
- 验收：工具执行时日志实时出现（不等到最后才显示）

### Task 5: 打断机制
- 测试：`test_interrupt.py`
- 实施：interrupt Event + 线程 + 每步检查 + 打断按钮
- 验收：点打断后 1-2s 内停止执行，UI 恢复等待状态

### Task 6: 时间戳日志
- 测试：`test_timestamp_log.py`
- 实施：每条日志加 `[HH:MM:SS.mmm]` 前缀 + [类型] 标记
- 验收：日志行有时间戳，类型标记正确

### Task 7: grep 工具
- 测试：`test_grep_tool.py`
- 实施：`tools/grep_ops.py` + 注册到 registry
- 验收：能在目录递归搜索，匹配行高亮

### Task 8: diff 工具
- 测试：`test_diff_tool.py`
- 实施：`tools/diff_ops.py` + 注册
- 验收：两文件对比输出差异行

### Task 9: process_status 工具
- 测试：`test_process_status.py`
- 实施：`tools/process_ops.py`
- 验收：显示当前进程列表

### Task 10: 集成测试（端到端）
- 测试：`test_ui_integration.py`
- 实施：模拟完整多轮交互流程
- 验收：UI + REPL + 工具执行 + 实时日志 全部联通

---

## 实施顺序

```
Phase A: UI 基础（Task 1-3 顺序做）
Phase B: UI 增强（Task 4-6）
Phase C: 新工具（Task 7-9）
Phase D: 集成测试（Task 10）
```

**预计工作量：UI 部分 3-4 小时，工具部分 2-3 小时，测试 2 小时**

---

## 文件结构

```
MyAgent/
  agent/
    ui.py              # UI 主模块（新增）
    loop_v2.py         # 改造：支持 interrupt Event + 实时日志
  tools/
    grep_ops.py        # 新增
    diff_ops.py       # 新增
    process_ops.py    # 新增
    registry.py       # 追加注册
  tests/
    test_ui_skeleton.py
    test_console_layout.py
    test_llm_panel_layout.py
    test_realtime_log.py
    test_interrupt.py
    test_timestamp_log.py
    test_grep_tool.py
    test_diff_tool.py
    test_process_status.py
    test_ui_integration.py
  docs/
    plans/
      2026-05-24-myagent-tkinter-ui-design.md  (本文件)
```

---

## 放弃的想法（不可行）

1. ~~WebView 嵌入浏览器~~：Win7 IE 内核太老，无现代 WebView 支持
2. ~~curses TUI~~：Win7 cmd.exe 不支持 curses，Windows Terminal 才支持（但 Win7 没有）
3. ~~pyperclip 剪贴板~~：第三方库，Win7 环境可能 pip 版本老，不值得
4. ~~tkinter.ttk 主题~~：ttk 在 Win7 下样式不一致，用纯 tkinter 控件更稳
5. ~~asyncio 事件循环~~：tkinter 主循环不是 asyncio，用 queue + after_poll 更稳
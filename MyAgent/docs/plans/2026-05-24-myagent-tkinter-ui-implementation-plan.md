# MyAgent Tkinter UI 实施计划

**日期:** 2026-05-24  
**基于设计文档:** `2026-05-24-myagent-tkinter-ui-design.md`

---

## 概述

本计划将 MyAgent Tkinter UI 开发拆分为 4 个阶段、10 个任务，全部采用 TDD 驱动开发（Red→Green→Refactor），每个任务独立测试文件，Green 后立即 commit。

- **Phase A**: UI 基础骨架（3 任务，顺序执行）
- **Phase B**: UI 增强功能（3 任务，B1+B2 可并行，B3 在其后）
- **Phase C**: 新增工具（3 任务，可完全并行）
- **Phase D**: 端到端集成（1 任务，置于最后）

**约束速查：**
- 只用 tkinter + 标准库，Win7 Python 3.7.4 兼容
- 不 pip install 任何包
- 每任务一 commit（Green 后即 commit）

---

## Phase A: UI 基础

### Task A1: UI 骨架（基础窗口）

**Test file**: `tests/test_ui_skeleton.py`  
**Production file**: `MyAgent/agent/ui.py`

**RED Phase** (write failing test):
- 验证窗口标题为 "MyAgent v2"
- 验证左右分栏存在（PanedWindow），左边 ~400px，右边 ~500px
- 验证底部状态栏标签存在（初始文字 "状态: 等待输入"）
- 验证窗口可关闭（不卡死）

**GREEN Phase** (minimal implementation):
- `MyAgentWindow` 类：`__init__` 创建 root window、set title、PanedWindow 左右两格、状态栏 Frame+Label
- 窗口尺寸建议 `root.geometry("900x600")`，可 resize
- 状态栏文字 `_update_status("等待输入")`
- 无任何工具按钮，仅骨架

**REFACTOR Phase** (optional):
- 提取 `_create_layout()` 方法拆分左右面板创建逻辑

**Verify command**:
```bash
python -m pytest tests/test_ui_skeleton.py -v
```
**Expected**: 4 passed（窗口标题、分栏存在、状态栏存在、可关闭）

**Dependencies**: 无

---

### Task A2: 控制台布局（左面板）

**Test file**: `tests/test_console_layout.py`  
**Production file**: `MyAgent/agent/ui.py`

**RED Phase** (write failing test):
- 验证"任务输入" Text 控件存在（3行高度，可编辑）
- 验证"开始任务" 按钮存在且文字正确
- 验证"执行过程监控" Text 控件存在（15行，只读）
- 验证"最终回答" Text 控件存在（5行，只读）
- 验证"清空日志" 按钮存在且文字正确
- 验证布局不重叠、不溢出

**GREEN Phase** (minimal implementation):
- 在左面板 PanedWindow child 内创建：
  - `Frame` + `Label("任务输入")` + `Text(height=3)`
  - `Frame` + `Button("开始任务")`
  - `Frame` + `Label("执行过程监控")` + `Text(height=15, state=DISABLED)`
  - `Frame` + `Label("最终回答")` + `Text(height=5, state=DISABLED)`
  - `Frame` + `Button("清空日志")`
- 各控件写入实例变量 `_task_input_text`、`_start_task_btn`、`_exec_log_text`、`_final_answer_text`、`_clear_log_btn`

**REFACTOR Phase** (optional):
- 提取 `_create_console_panel()` 方法

**Verify command**:
```bash
python -m pytest tests/test_console_layout.py -v
```
**Expected**: 6 passed（5 控件验证 + 1 布局不溢出）

**Dependencies**: A1（需要 PanedWindow 的左面板已存在）

---

### Task A3: LLM 交互区布局（右面板）

**Test file**: `tests/test_llm_panel_layout.py`  
**Production file**: `MyAgent/agent/ui.py`

**RED Phase** (write failing test):
- 验证"Prompt 文本" Text 控件存在（10行，只读，可滚动）
- 验证"复制 prompt" 按钮存在且文字正确
- 验证"Response 粘贴区" Text 控件存在（10行，可编辑）
- 验证"粘贴 & 提交" 按钮存在且文字正确
- 验证剪贴板复制逻辑（mock tkinter.clipboard，确认 copy 调用）
- 验证提交按钮 callback 存在（不测逻辑，只测 callback 是否绑定）

**GREEN Phase** (minimal implementation):
- 在右面板 PanedWindow child 内创建：
  - `Frame` + `Label("Prompt 文本")` + `Text(height=10, state=DISABLED)` + `Scrollbar`
  - `Button("复制 prompt")` — 点击复制 prompt Text 内容到系统剪贴板（`clipboard_clear()` + `clipboard_append()`）
  - `Frame` + `Label("Response 粘贴区")` + `Text(height=10)`
  - `Button("粘贴 & 提交")` — callback 绑定 `_on_response_submit()`
- 实例变量：`_prompt_text`、`_copy_prompt_btn`、`_response_text`、`_submit_response_btn`
- 复制用 tkinter 内置剪贴板，不引入第三方库

**REFACTOR Phase** (optional):
- 提取 `_create_llm_panel()` 方法
- 提取 `_copy_to_clipboard(text)` helper

**Verify command**:
```bash
python -m pytest tests/test_llm_panel_layout.py -v
```
**Expected**: 5 passed（4 控件 + 1 布局检查）

**Dependencies**: A1（需要 PanedWindow 的右面板已存在）

---

## Phase B: UI 增强

### Task B1: 实时日志（Queue + after_poll）

**Test file**: `tests/test_realtime_log.py`  
**Production file**: `MyAgent/agent/ui.py`

**RED Phase** (write failing test):
- 验证 `_log_queue` 为 `queue.Queue` 实例
- 验证 `_poll_log_queue()` 方法存在（每 100ms 从 queue 读日志并 `insert` 到 `_exec_log_text`）
- 验证 `root.after(100, self._poll_log_queue)` 能被调用（不卡主线程）
- 验证工具线程调用 `queue.put()` 后，主循环 poll 能捕获到日志并插入 Text
- 验证 Text insert 后 `see(END)` 被调用（日志自动滚到底部）

**GREEN Phase** (minimal implementation):
- `__init__` 中初始化 `self._log_queue = queue.Queue()`
- 实现 `_poll_log_queue()`:
  ```python
  def _poll_log_queue(self):
      while True:
          try:
              entry = self._log_queue.get_nowait()
              self._exec_log_text.insert(END, entry + "\n")
              self._exec_log_text.see(END)
          except queue.Empty:
              break
      self._root.after(100, self._poll_log_queue)
  ```
- `root.after(100, self._poll_log_queue)` 在 `__init__` 末尾启动 poll 循环
- 提供 `append_log(msg)` 方法供执行线程调用（`self._log_queue.put(msg)`）
- 当 `_exec_log_text` 处于 DISABLED 状态时，insert 前临时改为 NORMAL，完成后改回 DISABLED

**REFACTOR Phase** (optional):
- 提取 `_insert_log_safe(text)` 处理 DISABLED 状态切换

**Verify command**:
```bash
python -m pytest tests/test_realtime_log.py -v
```
**Expected**: 5 passed（queue 初始化、poll 方法、日志捕获、滚动到底部、DISABLED 安全插入）

**Dependencies**: A2（依赖 `_exec_log_text` 控件已存在）

---

### Task B2: 打断机制（线程 + Event + poll）

**Test file**: `tests/test_interrupt.py`  
**Production file**: `MyAgent/agent/ui.py`

**RED Phase** (write failing test):
- 验证 `_interrupt_event` 为 `threading.Event` 实例
- 验证打断按钮 `_interrupt_btn` 存在且文字为 "打断"
- 验证新任务按钮 `_new_task_btn` 存在且文字为 "新任务"
- 验证点击"打断"调用 `interrupt_event.set()`
- 验证 `_is_interrupted()` 返回 `interrupt_event.is_set()`
- 验证 `_reset_interrupt()` 调用 `interrupt_event.clear()`
- 验证执行线程每步检查 `_is_interrupted()`（mock 时间，确认提前退出）

**GREEN Phase** (minimal implementation):
- `__init__` 中初始化 `self._interrupt_event = threading.Event()`
- 实现方法：
  - `_interrupt()` → `self._interrupt_event.set()`
  - `_is_interrupted()` → `self._interrupt_event.is_set()`
  - `_reset_interrupt()` → `self._interrupt_event.clear()`
- "打断"按钮 callback 绑定 `_interrupt()`
- "新任务"按钮 callback 绑定 `_interrupt()` + `_clear_task_state()`（清空输入框和日志）
- `_execute_task_async()` 在执行线程的每步工具调用循环中检查 `_is_interrupted()`，若为 True 则 raise `InterruptedError` 或设置标志位提前 return
- UI 线程在 poll 循环中检测到打断后调用 `_reset_interrupt()` 并更新状态为 "已打断"

**REFACTOR Phase** (optional):
- 自定义 `InterruptedError` 异常类
- 提取 `_execute_in_thread(target_func)` 方法统一线程启动逻辑

**Verify command**:
```bash
python -m pytest tests/test_interrupt.py -v
```
**Expected**: 6 passed（Event 实例、按钮存在、set/clear/is_set、打断回调绑定、提前退出验证）

**Dependencies**: A2 + B1（依赖左面板按钮控件已存在，日志队列已就绪）

---

### Task B3: 时间戳日志（HH:MM:SS.mmm + 类型标记）

**Test file**: `tests/test_timestamp_log.py`  
**Production file**: `MyAgent/agent/ui.py`

**RED Phase** (write failing test):
- 验证 `_format_log(entry, tag)` 方法存在，返回 `"HH:MM:SS.mmm  [TAG]  entry"` 格式
- 验证时间戳格式正则：`^\d{2}:\d{2}:\d{2}\.\d{3}$`
- 验证类型标记支持：`[INPUT]`、`[PROMPT]`、`[TOOL]`、`[STEP]`、`[FINAL]`、`[ERROR]`、`[INTERRUPT]`
- 验证日志插入 Text 前已格式化（含时间戳前缀）
- 验证 `append_log(tag, msg)` 方法存在（自动加时间戳）

**GREEN Phase** (minimal implementation):
- 新增 `_format_log(msg, tag)` 方法：
  ```python
  from datetime import datetime

  def _format_log(self, msg, tag="[TOOL]"):
      ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
      return f"{ts}  {tag}  {msg}"
  ```
- `append_log(tag, msg)` 方法内部调用 `_format_log(tag, msg)` 后 `queue.put()`
- 各工具调用处、日志标记处替换为带时间戳格式：
  - 开始任务 → `[INPUT]`
  - Prompt 生成 → `[PROMPT]`
  - 工具执行 → `[TOOL]`
  - LLM 步骤 → `[STEP]`
  - 最终答案 → `[FINAL]`
  - 错误 → `[ERROR]`
  - 打断 → `[INTERRUPT]`

**REFACTOR Phase** (optional):
- 定义 `LOG_TAG_*` 常量类常量，避免字符串硬编码

**Verify command**:
```bash
python -m pytest tests/test_timestamp_log.py -v
```
**Expected**: 5 passed（时间戳格式、6 种 tag、append_log 整合、Text 格式化插入、边界 msg 测试）

**Dependencies**: B1（依赖 `append_log` 已定义，B2 依赖打断标记）

---

## Phase C: 新增工具

### Task C1: grep 工具

**Test file**: `tests/test_grep_tool.py`  
**Production file**: `MyAgent/tools/grep_ops.py`

**RED Phase** (write failing test):
- 验证 `grep(directory, keyword, recursive=False, case_sensitive=True)` 函数存在
- 验证非递归模式下只搜当前目录文件
- 验证递归模式下搜子目录
- 验证大小写敏感/不敏感两种模式
- 验证返回值格式为 `List[Dict[str, str]]`，每条记录含 `{"file": path, "line": lineno, "content": matched_text}`
- 验证目录不存在时报 `FileNotFoundError`
- 验证 keyword 为空时报 `ValueError`

**GREEN Phase** (minimal implementation):
- `grep_ops.py` 实现：
  - `import os, re`
  - 扫描目录 `os.listdir(dir)`，若 `recursive` 则 `os.walk(dir)`
  - 读取每个 `.py`/`.txt`/`.md` 等文本文件（`.bin` 等跳过）
  - 行级匹配：`re.search(keyword, line, flags)`（case_insensitive 时加 `re.I`）
  - 构造结果列表返回
  - 空 keyword 抛 `ValueError`，不存在目录抛 `FileNotFoundError`

**REFACTOR Phase** (optional):
- 提取 `_scan_file(path, keyword, case_sensitive)` 内部函数
- 限制最大文件数（避免扫描过多）和最大结果数

**Verify command**:
```bash
python -m pytest tests/test_grep_tool.py -v
```
**Expected**: 7 passed（基础搜索、递归、非递归、大小写、空 keyword、目录不存在、返回格式）

**Dependencies**: 无

---

### Task C2: diff 工具

**Test file**: `tests/test_diff_tool.py`  
**Production file**: `MyAgent/tools/diff_ops.py`

**RED Phase** (write failing test):
- 验证 `diff(file1_path, file2_path)` 函数存在
- 验证返回值格式为 `{"status": "identical"|"different"|"error", "diffs": List[Dict], "message": str}`
- 验证 `diffs` 每条记录含 `{"type": "-"|"+"|" ", "line_no": int, "content": str}`
- 验证两文件完全相同时 `status="identical"`
- 验证两文件不同时 `status="different"` 且 `diffs` 列出所有差异行
- 验证文件不存在时 `status="error"`，`message` 含错误信息

**GREEN Phase** (minimal implementation):
- `diff_ops.py` 实现：
  - 读取两文件内容，`splitlines(True)` 保留行尾
  - 使用 `difflib.unified_diff` 生成统一 diff
  - 解析 diff 输出为结构化列表
  - 文件不存在或读取失败时捕获 IOError/OSError
- 仅实现统一 diff 格式（`unified_diff` 是标准库，无需引入外部库）

**REFACTOR Phase** (optional):
- 提取 `_parse_diff_lines(lines)` 解析函数
- 支持 side-by-side diff 选项（flag 参数）

**Verify command**:
```bash
python -m pytest tests/test_diff_tool.py -v
```
**Expected**: 6 passed（identical 文件、different 文件、缺失文件1、缺失文件2、差异行格式、空 diff）

**Dependencies**: 无

---

### Task C3: process_status 工具

**Test file**: `tests/test_process_status.py`  
**Production file**: `MyAgent/tools/process_ops.py`

**RED Phase** (write failing test):
- 验证 `process_status()` 函数存在
- 验证返回值格式为 `{"processes": List[Dict], "summary": Dict}`
- 验证 `processes` 每条含 `{"pid": int, "name": str, "cpu_percent": float, "memory_mb": float}`
- 验证 `summary` 含 `{"total": int, "total_memory_gb": float}`
- 验证能列出当前进程（至少含 python.exe）

**GREEN Phase** (minimal implementation):
- `process_ops.py` 实现（纯标准库）：
  - Windows：`psutil` 不可用，改用 `os.popen("tasklist /FO CSV /NH")` + `csv` 模块解析
  - 或 `subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True)` 
  - 解析 CSV 输出提取 PID、进程名、内存使用
  - CPU 使用率：`wmic process where "name='python.exe'" get ProcessId,WorkingSetSize` 或跳过（Win7 兼容）
  - 返回结构化字典
- Win7 Python 3.7 兼容：无 `psutil`，全用 `subprocess` + `csv`

**REFACTOR Phase** (optional):
- 跨平台抽象：`if os.name == "nt"` 用 `tasklist`，`else` 用 `ps` 命令
- 添加"最耗内存进程 Top5"统计

**Verify command**:
```bash
python -m pytest tests/test_process_status.py -v
```
**Expected**: 4 passed（基础调用、返回格式、进程列表非空、CPU/内存字段存在）

**Dependencies**: 无

---

## Phase D: 集成测试

### Task D1: 端到端集成测试

**Test file**: `tests/test_ui_integration.py`  
**Production file**: `MyAgent/agent/ui.py`（集成所有模块）

**RED Phase** (write failing test):
- 验证完整 UI 初始化后所有控件同时存在（左面板 + 右面板 + 状态栏）
- 验证输入任务文本后点击"开始任务"，触发一轮模拟 REPL 循环（mock agent loop）
- 验证执行过程中日志实时出现（队列非空 + Text 插入）
- 验证执行完成后"最终回答" Text 有内容
- 验证"复制 prompt" 按钮可正常工作（mock clipboard）
- 验证"粘贴 & 提交" 能读取 Response 区内容并触发回调
- 验证"打断" 按钮能立即中断执行线程
- 验证"新任务" 按钮清空所有状态并重置 UI

**GREEN Phase** (minimal implementation):
- 创建集成测试文件 `test_ui_integration.py`
- 使用 `unittest.mock.patch` 模拟 `agent/loop_v2.py` 的 `_execute_once()` 方法（返回模拟的 prompt/response）
- 使用 `queue.Queue` mock 或真实队列验证日志流转
- UI 初始化走真实流程（`MyAgentWindow()`），不启动 `root.mainloop()`（用 `root.update()` 代替）
- 测试场景：
  1. 初始化 → 状态栏显示"等待输入"
  2. 输入任务 → 点击开始 → mock 工具执行 + 日志队列 → Text 实时更新 → 最终答案出现
  3. 打断 → 1s 内停止执行
  4. 新任务 → 所有状态清空
- 确认 `append_log` 方法在各工具执行处被正确调用（通过 mock 或 spy）

**REFACTOR Phase** (optional):
- 提取 `_simulate_repl_cycle()` helper 模拟多轮对话
- 添加性能测试（UI 响应时间 < 200ms）

**Verify command**:
```bash
python -m pytest tests/test_ui_integration.py -v
```
**Expected**: 8 passed（全控件初始化、日志实时性、最终答案、打断、新任务、复制 prompt、提交 response、状态流转）

**Dependencies**: A1 + A2 + A3 + B1 + B2 + B3 + C1 + C2 + C3（所有前序任务必须通过）

---

## 任务依赖图

```
A1 → A2 → A3
            ↓
       (B1 ‖ B2) → B3
       
C1, C2, C3 (完全独立，可并行)

D1 ← (A1+A2+A3 + B1+B2+B3 + C1+C2+C3 全部完成后)
```

## 实施顺序建议

```bash
# Phase A
git commit -m "A1: UI skeleton - basic window + PanedWindow"

# Phase B（先 B1+B2 并行，再 B3）
git commit -m "B1: realtime log - Queue + after_poll"
git commit -m "B2: interrupt - thread + Event + poll"
git commit -m "B3: timestamp log - HH:MM:SS.mmm markers"

# Phase C（3 任务完全并行，可同时开发）
git commit -m "C1: grep tool - recursive directory search"
git commit -m "C2: diff tool - file diff"
git commit -m "C3: process_status tool - process list"

# Phase D
git commit -m "D1: end-to-end integration test"
```

## 验收检查清单

| 阶段 | 任务 | 测试文件 | 测试通过 |
|------|------|---------|---------|
| A | A1 | `test_ui_skeleton.py` | ☐ |
| A | A2 | `test_console_layout.py` | ☐ |
| A | A3 | `test_llm_panel_layout.py` | ☐ |
| B | B1 | `test_realtime_log.py` | ☐ |
| B | B2 | `test_interrupt.py` | ☐ |
| B | B3 | `test_timestamp_log.py` | ☐ |
| C | C1 | `test_grep_tool.py` | ☐ |
| C | C2 | `test_diff_tool.py` | ☐ |
| C | C3 | `test_process_status.py` | ☐ |
| D | D1 | `test_ui_integration.py` | ☐ |

**总计：10 任务，10 个测试文件，全部通过后视为完整实现。**
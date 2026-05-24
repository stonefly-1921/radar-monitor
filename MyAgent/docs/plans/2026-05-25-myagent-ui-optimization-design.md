# MyAgent Tkinter UI 优化设计文档

**日期:** 2026-05-25  
**版本:** v2.1  
**基于:** `2026-05-24-myagent-tkinter-ui-design.md`

---

## 概述

本文档描述 Phase 2 完成的 UI 五大优化，以及 Phase 3 的 UI-REPL 集成。

---

## 优化 1: 合并监视过程 + 最终回复

### 问题
两个独立 Text 控件（执行过程监控 + 最终回答）造成界面碎片化，用户需要来回切换。

### 方案
合并为**单一面板**，格式：

```
--- 执行过程 ---
[11:23:05.123] [USER]  开始任务: 你好，简单介绍自己
[11:23:06.234] [AGENT] 思考: 我需要调用 MiniMax API
[11:23:06.891] [TOOL]   调用 grep 工具，查询文件...
[11:23:08.102] [TOOL]   grep 返回: 5 matches
[11:23:10.555] [AGENT]  最终回答:
======================================
我是一个AI助手，可以帮助你解答问题、提供信息。

我在以下方面可以帮你：
- 回答问题和提供信息
- 进行对话和交流
======================================
```

**格式规则：**
- 每条日志：`HH:MM:SS.mmm  [TYPE]  消息`
- TYPE: `USER` / `AGENT` / `TOOL` / `SYSTEM` / `ERROR`
- 最终回答前插入 `=== 最终回答 ===` 分隔符
- 分隔符以上的为执行过程，分隔符以下的为最终回答
- 用户可通过 Ctrl+B 收藏/标注重要段落
- readonly，但可选中复制

### 实现
- 删除 `_final_answer_text` 及其 Frame
- `_exec_log_text` 改为可滚动容器，承载所有内容
- 新增方法 `_write_final_answer(text)` 在分隔符后插入最终回答
- 保留 `_exec_log_text` 作为唯一日志容器

---

## 优化 2: 一键启动（双击 py 直接运行）

### 问题
需要手动打开前端（ui.py）+ 后端（REPL），太麻烦。

### 方案
`agent/ui.py` 是唯一入口，双击直接运行：

```bash
python agent/ui.py
```

**架构：**
- UI 启动时自动启动 REPL 子进程（`loop_v2.py`）
- UI 和 REPL 通过文件（`io/input.txt`, `prompt.txt`, `response.txt`）通信
- UI 用 `subprocess.Popen` + `threading` 监控 REPL stdout
- 启动顺序：UI 初始化 → 启动 REPL 子进程 → UI mainloop()

**REPL 子进程管理：**
- `_repl_process`: subprocess.Popen 对象
- `_repl_reader_thread`: threading.Thread，持续读 stdout
- `_start_repl()`: 启动子进程，设置 PYTHONIOENCODING=utf-8
- `_stop_repl()`: terminate + wait
- `_poll_io_files()`: root.after() 轮询 io/ 目录下的文件变化

**io/ 目录文件：**
| 文件 | 方向 | 用途 |
|------|------|------|
| `input.txt` | UI → REPL | 任务输入 |
| `prompt.txt` | REPL → UI | 生成的 prompt |
| `response.txt` | UI → REPL | LLM 回复 |
| `final_answer.txt` | REPL → UI | 最终答案 |
| `status.txt` | REPL → UI | 状态更新（可选）|

**状态机：**
```
[IDLE] --点击开始任务--> [GENERATING_PROMPT] --prompt.txt出现--> [WAITING_RESPONSE]
--response.txt写入--> [PROCESSING] --final_answer.txt出现--> [IDLE]
```

**UI 入口（ui.py 末尾）：**
```python
if __name__ == '__main__':
    win = MyAgentWindow()
    win.start_repl()  # 启动 REPL 子进程
    win.mainloop()    # Tkinter 主循环
```

---

## 优化 3: 引导词提示

### 输入框 placeholder
- `_task_input_text` 初始显示：`"请在这里输入任务，输入 quit 退出..."`
- 字体颜色：`gray`
- 用户点击后自动清除
- 恢复条件：新任务开始后清空，输入框再次显示 placeholder

### 执行过程提示词（左侧面板）
| 场景 | 提示词 | 样式 |
|------|--------|------|
| 等待输入 | `请在上方输入任务，然后点击"开始任务"` | 蓝色斜体 |
| 正在生成 prompt | `正在生成 prompt，请稍候...` | 蓝色 |
| prompt 已生成 | `✅ prompt 已生成！请复制到 LLM，粘贴回复后点击"粘贴&提交"` | 绿色高亮 |
| 等待 response | `请在右侧"粘贴&提交"区域粘贴 LLM 回复，然后点击"粘贴&提交"` | 黄色 |
| 处理中 | `处理中，请稍候...` | 蓝色 |
| 完成 | `✅ 任务完成！查看下方结果` | 绿色 |
| 被中断 | `⚠️ 任务被用户中断` | 红色 |

### 新任务提示
- 任务完成后，`_task_input_text` 显示 placeholder
- 用户输入第一个字符后，placeholder 消失

---

## 优化 4: 执行过程实时反馈

### 状态栏（底部）
| 状态 | 显示 |
|------|------|
| IDLE | `状态: 就绪` |
| GENERATING_PROMPT | `状态: 正在生成 prompt...` |
| WAITING_RESPONSE | `状态: 等待 LLM 回复` |
| PROCESSING | `状态: 处理中 ({turn} 轮)` |
| IDLE with result | `状态: 完成 (耗时 Xs)` |

### prompt 自动显示
- `prompt.txt` 一旦出现内容，立即显示到 `_prompt_text`
- `_prompt_text` 设置 `state=tk.NORMAL`，写入后设回 `state=tk.DISABLED`

### 执行轮次显示
- 每执行一个工具，`_exec_log_text` 显示 `[TOOL] 调用工具: xxx`
- 轮次计数器显示在状态栏

---

## 优化 5: UI 美化

### 配色方案（现代感，深色主题）
| 元素 | 颜色 | 说明 |
|------|------|------|
| 主背景 | `#1e1e1e` | 深灰 |
| 面板背景 | `#252526` | 略浅灰 |
| 文字 | `#d4d4d4` | 浅灰白 |
| 主色调 | `#0078d4` | 蓝色（Win10 风格） |
| 强调色 | `#0e639c` | 深蓝 |
| 成功绿 | `#4ec9b0` | 青绿 |
| 警告黄 | `#dcdcaa` | 淡黄 |
| 错误红 | `#f14c4c` | 红色 |
| USER 日志 | `#9cdcfe` | 浅蓝 |
| AGENT 日志 | `#d7ba7d` | 金色 |
| TOOL 日志 | `#4ec9b0` | 青绿 |
| SYSTEM 日志 | `#808080` | 灰色 |

### 字体
- 主字体：`"Segoe UI", 9`（系统默认）
- 日志字体：`"Cascadia Code", "Consolas", 9`（等宽）
- 按钮字体：`"Segoe UI", 9, bold`

### 窗口
- 默认大小：`1200x800`
- 最小大小：`900x600`
- 可调整大小
- 标题：`MyAgent v2.1`

### 按钮样式
- 背景：`#0e639c`
- 文字：`white`
- Hover：`#1177bb`
- Active：`#095c8f`
- Border radius：视觉上的圆角（通过 padding 实现）

### 面板间距
- 左右面板比例：45% : 55%
- 内边距：统一 `padx=10, pady=5`

---

## Phase 3: UI-REPL 集成（核心功能）

### `_on_start_task` 实现

```python
def _on_start_task(self):
    """开始任务按钮回调。"""
    user_input = self._task_input_text.get("1.0", tk.END).strip()
    if not user_input or user_input == self._placeholder_text:
        self.update_status("状态: 请先输入任务")
        return

    # 写入 io/input.txt
    with open(self._io_dir / 'input.txt', 'w', encoding='utf-8') as f:
        f.write(user_input)

    # 清空输入框，显示 placeholder
    self._task_input_text.delete("1.0", tk.END)
    self._task_input_text.insert("1.0", self._placeholder_text)
    self._task_input_text.configure(fg="gray")

    # 更新状态
    self._set_state('GENERATING_PROMPT')
    self.append_log("USER", f"开始任务: {user_input}")

    # 通知 REPL 进程（写 stdin 或发信号）
    self._notify_repl()
```

### `_poll_io_files` 轮询逻辑

```python
def _poll_io_files(self):
    """轮询 io/ 目录，处理文件更新。"""
    # 检查 prompt.txt 是否有新内容
    prompt_file = self._io_dir / 'prompt.txt'
    if prompt_file.exists():
        content = prompt_file.read_text(encoding='utf-8').strip()
        if content and content != self._last_prompt:
            self._last_prompt = content
            self._show_prompt(content)
            self._set_state('WAITING_RESPONSE')
            self.append_log("SYSTEM", "✅ prompt 已生成！请复制到 LLM，粘贴回复后点击"粘贴&提交"")

    # 检查 final_answer.txt
    final_file = self._io_dir / 'final_answer.txt'
    if final_file.exists():
        content = final_file.read_text(encoding='utf-8').strip()
        if content and content != self._last_final:
            self._last_final = content
            self._write_final_answer(content)
            self._set_state('IDLE')
            self.append_log("SYSTEM", "✅ 任务完成！")

    # 继续轮询
    self.root.after(500, self._poll_io_files)
```

### `_on_submit_response` 实现

```python
def _on_submit_response(self):
    """读取 response 区域内容，写入 response.txt。"""
    resp = self._response_text.get("1.0", tk.END).strip()
    if not resp:
        self.update_status("状态: response 区域为空，请先粘贴 LLM 回复")
        return

    response_file = self._io_dir / 'response.txt'
    response_file.write_text(resp, encoding='utf-8')

    self._response_text.delete("1.0", tk.END)
    self._set_state('PROCESSING')
    self.append_log("USER", "已提交 LLM 回复，等待处理...")
    self._notify_repl()
```

---

## 文件变更清单

| 文件 | 变更类型 |
|------|----------|
| `agent/ui.py` | 重构：合并面板 + 引导词 + 美化 + REPL 集成 |
| `agent/loop_v2.py` | 小改：支持被 ui.py 作为子进程调用 |
| `tests/test_ui_integration.py` | 更新：测试新的合并布局 |
| `tests/test_repl_integration.py` | 新增：测试 REPL 集成 |

---

## 任务拆分（Phase 3）

| 任务 | 内容 | 测试 |
|------|------|------|
| Task E1 | UI-REPL 集成核心逻辑 | `test_repl_integration.py` |
| Task E2 | 合并执行过程+最终回答面板 | `test_merged_log_panel.py` |
| Task E3 | 引导词 + 状态提示系统 | `test_guided_prompts.py` |
| Task E4 | UI 美化（配色+字体+按钮） | visual verification |
| Task E5 | 一键启动（ui.py 主入口） | 双击运行测试 |

---

**下一步：** 用户确认设计后，启动 Phase 3 实现。
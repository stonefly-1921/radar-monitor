# ⚠️ DEPRECATED — Dark Theme Design (v2.1)

**This document describes the abandoned dark theme design.**

     1|# MyAgent UI 自动化操作指南
     2|
     3|> 本文档记录如何通过 Windows GUI 自动化操作 MyAgent Tkinter 界面，模拟人工操作完成多轮 REPL 对话。
     4|
     5|## 一、系统架构
     6|
     7|```
     8|用户 ←→ MyAgent UI (Tkinter) ←→ REPL 子进程 (loop_v2.py) ←→ 文件 IO
     9|                          ↑
    10|                          └── pywinauto 自动化驱动
    11|```
    12|
    13|**三个关键文件**（文件模式 REPL）：
    14|- `io/input.txt` - 用户输入的任务
    15|- `io/prompt.txt` - LLM 的输入（MyAgent 生成）
    16|- `io/response.txt` - LLM 的输出（人工粘贴）
    17|- `io/final_answer.txt` - 最终答案（REPL 处理完后写入）
    18|
    19|**UI 进程**：PID 18012，标题 "MyAgent v2.1"，Tkinter 窗口
    20|
    21|**REPL 子进程**：由 UI 的 `start()` 方法启动，跑 `agent/loop_v2.py`，通过 pipe 与 UI 通信
    22|
    23|---
    24|
    25|## 二、控件坐标映射
    26|
    27|通过 `pywinauto` 分析 MyAgent v2.1 窗口，得到以下关键控件：
    28|
    29|| 控件 | HWND | 坐标 L,T,R,B | 说明 |
    30||------|------|-------------|------|
    31|| 任务输入框 | 13700270 | 80,172,858,282 | 左侧顶部 Text 控件 |
    32|| 开始任务按钮 | 265380 | 80,290,858,358 | 左侧"开始任务"按钮 |
    33|| 日志区域 | 330918 | 80,378,858,1490 | 左侧执行过程日志（只读） |
    34|| Prompt 文本区 | 330868 | 886,168,2422,782 | 右侧 Prompt 显示区（只读） |
    35|| Response 文本区 | 28838998 | 886,900,2422,1516 | 右侧 Response 输入区（可编辑） |
    36|| 粘贴&提交按钮 | 15273062 | 886,1522,2456,1582 | 右侧提交按钮 |
    37|| 新任务按钮 | 43191100 | 80,1580,858,1648 | 左下"新任务"按钮 |
    38|
    39|---
    40|
    41|## 三、操作流程
    42|
    43|### 3.1 连接 UI 窗口
    44|
    45|```python
    46|from pywinauto import Application
    47|
    48|app = Application(backend="win32").connect(process=18012)
    49|win = app.window(title="MyAgent v2.1")
    50|```
    51|
    52|### 3.2 输入任务到 UI
    53|
    54|Tkinter Text 控件不是标准 Edit 控件，`set_edit_text()` 不起作用，必须用键盘模拟：
    55|
    56|```python
    57|import pywinauto.keyboard as kb
    58|
    59|# 点击任务输入框
    60|task_input = [c for c in win.children() if c.handle == 13700270][0]
    61|task_input.click_input()
    62|time.sleep(0.3)
    63|
    64|# 全选清空
    65|kb.send_keys('^a')
    66|time.sleep(0.1)
    67|kb.send_keys('{DELETE}')
    68|
    69|# 设置剪贴板内容
    70|subprocess.run(['powershell', '-Command', f'Set-Clipboard -Value "{task_text}"'], capture_output=True)
    71|time.sleep(0.3)
    72|
    73|# 粘贴
    74|kb.send_keys('^v')
    75|time.sleep(0.5)
    76|```
    77|
    78|### 3.3 点击开始任务
    79|
    80|```python
    81|start_btn = [c for c in win.children() if c.handle == 265380][0]
    82|start_btn.click_input()
    83|```
    84|
    85|### 3.4 等待 prompt 生成
    86|
    87|轮询 `io/prompt.txt`，直到出现内容：
    88|
    89|```python
    90|import os
    91|def wait_for_prompt(io_dir, timeout=30):
    92|    prompt_file = os.path.join(io_dir, "prompt.txt")
    93|    start = time.time()
    94|    while time.time() - start < timeout:
    95|        if os.path.exists(prompt_file):
    96|            size = os.path.getsize(prompt_file)
    97|            if size > 0:
    98|                content = open(prompt_file, encoding='utf-8').read().strip()
    99|                if content:
   100|                    return content
   101|        time.sleep(1)
   102|    return None
   103|```
   104|
   105|### 3.5 粘贴 Response 并提交
   106|
   107|```python
   108|# 点击 response 文本区
   109|resp_input = [c for c in win.children() if c.handle == 28838998][0]
   110|resp_input.click_input()
   111|time.sleep(0.3)
   112|
   113|# 全选清空
   114|kb.send_keys('^a')
   115|time.sleep(0.1)
   116|kb.send_keys('{DELETE}')
   117|
   118|# 设置剪贴板并粘贴
   119|subprocess.run(['powershell', '-Command', f'Set-Clipboard -Value "{response_text[:5000]}"'], capture_output=True)
   120|time.sleep(0.3)
   121|kb.send_keys('^v')
   122|time.sleep(0.5)
   123|
   124|# 点击提交按钮
   125|submit_btn = [c for c in win.children() if c.handle == 15273062][0]
   126|submit_btn.click_input()
   127|```
   128|
   129|---
   130|
   131|## 四、完整自动化循环
   132|
   133|```
   134|启动/连接 UI
   135|    ↓
   136|输入任务 → 点击开始任务
   137|    ↓
   138|轮询等待 prompt 生成
   139|    ↓
   140|复制 prompt → 调用 LLM API → 获取 response
   141|    ↓
   142|粘贴 response → 点击提交
   143|    ↓
   144|REPL 处理工具调用（等待若干秒）
   145|    ↓
   146|检查 final_answer.txt → 有则完成
   147|    ↓
   148|否则：读取新 prompt → 继续循环
   149|```
   150|
   151|### LLM 调用
   152|
   153|AFSIM 使用 minimax API，URL：`https://api.minimaxi.com/anthropic/v1/messages`
   154|
   155|需要 `MINIMAX_API_KEY` 环境变量（需在系统环境变量中设置，或在启动 REPL 子进程时传入）。
   156|
   157|---
   158|
   159|## 五、已知限制与解决方案
   160|
   161|| 问题 | 原因 | 解决 |
   162||------|------|------|
   163|| `set_edit_text()` 对 Tkinter Text 不生效 | Tkinter HwndWrapper 不支持该方法 | 用 Ctrl+A 全选 + Ctrl+V 粘贴 |
   164|| 剪贴板被占用导致 `OpenClipboard` 失败 | 其他进程持有剪贴板锁 | 用 PowerShell 的 `Set-Clipboard` 替代 |
   165|| io/input.txt 为空 | REPL 子进程未启动 | 需确保 UI 的 `start()` 方法被调用（不是直接 `python ui.py`） |
   166|| prompt.txt 始终为空 | REPL 子进程没有运行 | 重新启动 UI（需调用 `start()` 初始化） |
   167|
   168|---
   169|
   170|## 六、快速诊断命令
   171|
   172|```powershell
   173|# 检查 MyAgent 进程
   174|Get-Process | Where-Object {$_.ProcessName -match "python" -and $_.MainWindowTitle -match "MyAgent"}
   175|
   176|# 列出所有子控件
   177|python -c "
   178|from pywinauto import Application
   179|app = Application(backend='win32').connect(process=18012)
   180|win = app.window(title='MyAgent v2.1')
   181|for c in win.children():
   182|    try:
   183|        r = c.rectangle()
   184|        print(f'HWND={c.handle} L={r.left},T={r.top},R={r.right},B={r.bottom} [{c.class_name}]')
   185|    except: pass
   186|"
   187|
   188|# 检查 io 文件状态
   189|Get-ChildItem C:\Users\15041\.openclaw\workspace\MyAgent\io | Select-Object Name,Length
   190|```
   191|
   192|---
   193|
   194|## 七、启动 MyAgent UI 的正确方式
   195|
   196|不要直接 `python ui.py`，而要让 Tkinter 应用调用 `start()` 方法：
   197|
   198|```python
   199|# 方法1：通过代码启动
   200|from agent.ui import MyAgentWindow
   201|root = tk.Tk()
   202|ui = MyAgentWindow(root)
   203|ui.start()  # 启动 REPL 子进程
   204|root.mainloop()
   205|
   206|# 方法2：确保已有进程（PID=18012）已正确启动
   207|# 检查 io/prompt.txt 是否有内容可以判断 REPL 是否在运行
   208|```
   209|
   210|---
   211|
   212|_本文档基于 MyAgent v2.1 UI 自动化测试结果生成_
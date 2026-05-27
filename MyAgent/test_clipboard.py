"""直接通过剪贴板+Win32消息操作 Tkinter Text 控件"""
from pywinauto import Application
import time, os, subprocess

# 先清空剪贴板
subprocess.run(['cmd', '/c', 'echo off | clip'], capture_output=True)

app = Application(backend='win32').connect(process=18012)
win = app.window(title='MyAgent v2.1')

task_text = '测试：从UI自动化输入任务'

# 步骤1：设置剪贴板内容
import win32clipboard
win32clipboard.OpenClipboard()
win32clipboard.EmptyClipboard()
win32clipboard.SetClipboardText(task_text, win32clipboard.CF_TEXT)
win32clipboard.CloseClipboard()
print(f'剪贴板已设置: {task_text[:30]}')

# 步骤2：点击任务输入框（HWND=13700270）并粘贴
task_input = None
for c in win.children():
    if c.handle == 13700270:
        task_input = c
        break

if task_input:
    task_input.click_input()
    time.sleep(0.3)
    
    import pywinauto.keyboard as kb
    kb.send_keys('^v')
    time.sleep(0.5)
    print('已粘贴')

# 步骤3：点击开始任务按钮（HWND=265380）
start_btn = None
for c in win.children():
    if c.handle == 265380:
        start_btn = c
        break

if start_btn:
    start_btn.click_input()
    print('已点击开始任务')

time.sleep(2)

# 检查 io/input.txt
f = r'C:\Users\15041\.openclaw\workspace\MyAgent\io\input.txt'
size = os.path.getsize(f)
print(f'io/input.txt 大小: {size}')
if size > 0:
    print(f'内容: {open(f, encoding="utf-8").read()[:200]}')
else:
    print('文件为空')
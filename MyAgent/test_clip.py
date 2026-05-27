"""MyAgent UI 自动化测试"""
from pywinauto import Application
import time, os, subprocess
import pywinauto.keyboard as kb

# 设置剪贴板内容（通过 PowerShell）
subprocess.run(['powershell', '-Command', "Set-Clipboard -Value 'AFSIM弹道测试任务'"], capture_output=True)
time.sleep(0.3)

app = Application(backend='win32').connect(process=18012)
win = app.window(title='MyAgent v2.1')

# 点击任务输入框并粘贴
task_input = None
for c in win.children():
    if c.handle == 13700270:
        task_input = c
        break

if task_input:
    task_input.click_input()
    time.sleep(0.3)
    kb.send_keys('^v')
    time.sleep(0.5)
    print('已粘贴到输入框')
else:
    print('未找到任务输入框')

# 点击开始任务按钮
start_btn = None
for c in win.children():
    if c.handle == 265380:
        start_btn = c
        break

if start_btn:
    start_btn.click_input()
    print('已点击开始任务')
else:
    print('未找到开始按钮')

time.sleep(3)

# 检查 io/input.txt
f = r'C:\Users\15041\.openclaw\workspace\MyAgent\io\input.txt'
size = os.path.getsize(f)
print(f'io/input.txt 大小: {size}')
if size > 0:
    content = open(f, encoding='utf-8').read()
    print(f'内容: {content[:200]}')
else:
    print('文件为空 - 检查 placeholder')

# 检查 prompt.txt
f2 = r'C:\Users\15041\.openclaw\workspace\MyAgent\io\prompt.txt'
size2 = os.path.getsize(f2)
print(f'io/prompt.txt 大小: {size2}')
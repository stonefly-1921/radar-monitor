"""继续 UI 自动化：提交 response 并等待结果"""
from pywinauto import Application
import time, os, subprocess
import pywinauto.keyboard as kb

app = Application(backend='win32').connect(process=18012)
win = app.window(title='MyAgent v2.1')

def find_control(win, hwnd):
    for c in win.children():
        if c.handle == hwnd:
            return c
    return None

# 读取 response.txt 确认内容
resp = open(r'C:\Users\15041\.openclaw\workspace\MyAgent\io\response.txt', encoding='utf-8').read().strip()
print(f'response.txt 内容: {resp[:100]}')

# 点击 response 文本区（HWND=28838998）
resp_input = find_control(win, 28838998)
if not resp_input:
    print('未找到 response 文本区')
    exit(1)

resp_input.click_input()
time.sleep(0.3)

# 全选清空
kb.send_keys('^a')
time.sleep(0.1)
kb.send_keys('{DELETE}')
time.sleep(0.1)

# 设置剪贴板并粘贴
subprocess.run(['powershell', '-Command', f'Set-Clipboard -Value "{resp}"'], capture_output=True)
time.sleep(0.5)
kb.send_keys('^v')
time.sleep(0.5)
print('已粘贴 response 到 UI')

# 点击粘贴&提交按钮（HWND=15273062）
submit_btn = find_control(win, 15273062)
if submit_btn:
    submit_btn.click_input()
    print('已点击粘贴&提交')
else:
    print('未找到提交按钮')

# 等待 REPL 处理
print('等待 REPL 处理...')
time.sleep(8)

# 检查 final_answer.txt
final_file = r'C:\Users\15041\.openclaw\workspace\MyAgent\io\final_answer.txt'
if os.path.exists(final_file):
    size = os.path.getsize(final_file)
    print(f'final_answer.txt 大小: {size}')
    if size > 0:
        content = open(final_file, encoding='utf-8').read().strip()
        print(f'最终答案: {content[:500]}')
else:
    print('final_answer.txt 不存在')

# 也检查 prompt.txt 是否有新内容
prompt_file = r'C:\Users\15041\.openclaw\workspace\MyAgent\io\prompt.txt'
if os.path.exists(prompt_file):
    size = os.path.getsize(prompt_file)
    print(f'prompt.txt 大小: {size}')
    if size > 0:
        content = open(prompt_file, encoding='utf-8').read().strip()
        print(f'新 prompt: {content[:300]}')
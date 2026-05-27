"""
验证：MyAgent UI 启动的 REPL 子进程 和 直接启动的 loop_v2.py 行为是否一致

目标：
1. 通过 UI 的"开始任务"按钮触发 REPL
2. 观察 io/ 文件变化
3. 理解 stdin 在两种场景下的差异

测试步骤：
1. 清空 io/
2. 通过 UI 输入任务 + 点击开始任务
3. 观察 input.txt 和 prompt.txt 的变化
4. 检查 REPL stdin 是否连接到了 UI
"""
import sys, os, time, subprocess
from pywinauto import Application
import pywinauto.keyboard as kb

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'
IO_DIR = os.path.join(MYAGENT_DIR, 'io')


def clean_io():
    for f in ['input.txt', 'response.txt', 'tool_result.json', 'final_answer.txt']:
        p = os.path.join(IO_DIR, f)
        if os.path.exists(p):
            open(p, 'w', encoding='utf-8').write('')


def show_io(label=''):
    if label:
        print(f'  [{label}]')
    for f in ['input.txt', 'prompt.txt', 'response.txt', 'final_answer.txt']:
        p = os.path.join(IO_DIR, f)
        if os.path.exists(p):
            size = os.path.getsize(p)
            content = open(p, encoding='utf-8').read().strip()[:80] if size > 0 else ''
            print(f'    {f}: {size}B | {content}')
        else:
            print(f'    {f}: (不存在)')


def get_win():
    app = Application(backend='win32').connect(process=18012)
    return app.window(title='MyAgent v2.1')


def find(hwnd):
    win = get_win()
    for c in win.children():
        if c.handle == hwnd:
            return c
    return None


def ui_input(hwnd, text):
    ctrl = find(hwnd)
    if not ctrl:
        return False
    ctrl.click_input()
    time.sleep(0.3)
    kb.send_keys('^a')
    time.sleep(0.1)
    kb.send_keys('{DELETE}')
    time.sleep(0.1)
    
    # 分段粘贴
    for i in range(0, len(text), 500):
        chunk = text[i:i+500]
        try:
            subprocess.run(
                ['powershell', '-Command', f'Set-Clipboard -Value "{chunk}"'],
                capture_output=True, timeout=5
            )
        except:
            pass
        time.sleep(0.3)
        kb.send_keys('^v')
        time.sleep(0.3)
    return True


def click_btn(hwnd):
    ctrl = find(hwnd)
    if ctrl:
        ctrl.click_input()
        return True
    return False


print('='*60)
print('UI-REPL 交互验证')
print('='*60)

# 清空 io
clean_io()
print('[清空] io/')
show_io('清空后')

# 输入任务
print('\n[输入] 任务...')
ui_input(13700270, '测试任务：1+1=2')
print('  输入完成')

# 点击开始任务
print('[开始] 点击开始任务...')
click_btn(265380)
print('  已点击')

# 等待 prompt 生成（最多 20 秒）
print('[等待] prompt 生成...')
prompt_path = os.path.join(IO_DIR, 'prompt.txt')
for i in range(20):
    time.sleep(1)
    if os.path.exists(prompt_path) and os.path.getsize(prompt_path) > 100:
        print(f'  {i+1}秒后 prompt.txt 出现')
        break
    if i % 5 == 4:
        show_io(f'{i+1}秒后')

print('\n[结果]')
show_io('结果')

# 读 prompt.txt
prompt = ''
if os.path.exists(prompt_path) and os.path.getsize(prompt_path) > 0:
    prompt = open(prompt_path, encoding='utf-8').read()
    print(f'\n[Prompt] 长度={len(prompt)} chars')
    print(f'[Prompt] 内容前200字: {prompt[:200]}')

# 检查 input.txt
input_path = os.path.join(IO_DIR, 'input.txt')
if os.path.exists(input_path) and os.path.getsize(input_path) > 0:
    input_content = open(input_path, encoding='utf-8').read()
    print(f'\n[Input] 长度={len(input_content)} chars: {input_content}')
else:
    print(f'\n[Input] input.txt 为空（0字节）')

print('\n[完成]')
"""
MyAgent UI 自动化 - 调试版（追踪 REPL 行为）
==============================================
"""
import time, json, subprocess, urllib.request, os
from pywinauto import Application
import pywinauto.keyboard as kb

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'
IO_DIR = rf'{MYAGENT_DIR}\io'
API_KEY = subprocess.run(
    ['powershell', '-Command', "[Environment]::GetEnvironmentVariable('MINIMAX_API_KEY', 'User')"],
    capture_output=True, text=True, encoding='utf-8'
).stdout.strip()


def find_myagent():
    from pywinauto import findwindows
    windows = findwindows.find_windows(title_re='MyAgent.*')
    return windows[0] if windows else None


def connect_ui():
    hwnd = find_myagent()
    if not hwnd:
        return None
    app = Application(backend='win32').connect(handle=hwnd)
    return app.window(handle=hwnd)


def find_controls_by_pos(win):
    controls = {}
    for c in win.children():
        try:
            r = c.rectangle()
            x, y = r.left, r.top
            if 200 < x < 300 and 200 < y < 300:
                controls['task_input'] = c
            elif 200 < x < 300 and 340 < y < 380:
                controls['start_btn'] = c
            elif 900 < x < 1100 and 900 < y < 1050:
                controls['response_input'] = c
            elif 900 < x < 1100 and 1550 < y < 1620:
                controls['submit_btn'] = c
        except:
            pass
    return controls


def ui_paste(ctrl, text):
    ctrl.click_input()
    time.sleep(0.3)
    kb.send_keys('^a')
    time.sleep(0.1)
    kb.send_keys('{DELETE}')
    for i in range(0, len(text), 500):
        try:
            subprocess.run(
                ['powershell', '-Command', f'Set-Clipboard -Value "{text[i:i+500]}"'],
                capture_output=True, timeout=5
            )
        except:
            pass
        time.sleep(0.3)
        kb.send_keys('^v')
        time.sleep(0.3)


def click_btn(ctrl):
    ctrl.click_input()


def call_llm(prompt_text):
    url = 'https://api.minimaxi.com/anthropic/v1/messages'
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json',
        'anthropic-version': '2023-06-01',
    }
    payload = {
        'model': 'MiniMax-M2.7',
        'messages': [{'role': 'user', 'content': prompt_text}],
        'max_tokens': 8192,
        'temperature': 0.7
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        for item in result.get('content', []):
            if item.get('type') == 'text':
                text = item.get('text', '').strip()
                if text:
                    try:
                        return json.loads(text)
                    except:
                        return {'action': 'final', 'answer': text}


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


def wait_prompt_change(old_size, timeout=20):
    prompt_path = os.path.join(IO_DIR, 'prompt.txt')
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(prompt_path):
            size = os.path.getsize(prompt_path)
            if size != old_size and size > old_size + 50:
                return size
        time.sleep(0.5)
    return None


# ============ 主流程 ============

print('=' * 60)
print('MyAgent UI 自动化 - 调试版')
print('=' * 60)

# 连接 UI
print('[连接] MyAgent UI...')
win = connect_ui()
if not win:
    print('  [失败] 未找到 MyAgent UI')
    exit(1)
print('  连接成功')

controls = find_controls_by_pos(win)
print(f'  找到控件: {list(controls.keys())}')

# 清空 io
clean_io()
print('[清空] io/')

# === 步骤1：输入任务 ===
print('\n[步骤1] 输入任务...')
ui_paste(controls['task_input'], '请计算 1+1 等于几')
print('  输入完成')

# === 步骤2：点击开始 ===
print('[步骤2] 点击开始任务...')
click_btn(controls['start_btn'])
print('  已点击')

# === 步骤3：等待 prompt ===
print('[步骤3] 等待 prompt 生成...')
prompt_path = os.path.join(IO_DIR, 'prompt.txt')
for i in range(20):
    time.sleep(1)
    if os.path.exists(prompt_path) and os.path.getsize(prompt_path) > 100:
        print(f'  {i+1}秒后 prompt 就绪')
        break

old_prompt_size = os.path.getsize(prompt_path) if os.path.exists(prompt_path) else 0
prompt = open(prompt_path, encoding='utf-8').read().strip()
print(f'  prompt 大小: {old_prompt_size} bytes, 长度: {len(prompt)} chars')

# === 步骤4：调用 LLM ===
print('\n[步骤4] 调用 LLM...')
result = call_llm(prompt)
if not result:
    print('  [失败] LLM 调用失败')
    exit(1)

action = result.get('action', '?')
print(f'  action={action}')
if result.get('answer'):
    print(f'  answer={result.get("answer")[:80]}')

response_json = json.dumps(result, ensure_ascii=False)
print(f'  response_json: {response_json[:100]}...')

# === 步骤5：写 response.txt + 等待 REPL 处理 ===
print('\n[步骤5] 写 response.txt...')
open(os.path.join(IO_DIR, 'response.txt'), 'w', encoding='utf-8').write(response_json)
print(f'  已写入 {len(response_json)} chars')

# 粘贴到 UI
print('[步骤6] 粘贴到 UI...')
ui_paste(controls['response_input'], response_json)
time.sleep(0.5)

# 点击提交
print('[步骤7] 点击提交按钮...')
click_btn(controls['submit_btn'])
print('  已点击')

# 轮询 io/ 文件变化（频繁检查）
print('\n[步骤8] 轮询 io/ 变化 (20s)...')
print('  开始时间:', time.strftime('%H:%M:%S'))
t0 = time.time()
found_final = False

while time.time() - t0 < 20:
    changed = []
    for f in ['input.txt', 'prompt.txt', 'response.txt', 'final_answer.txt']:
        p = os.path.join(IO_DIR, f)
        if os.path.exists(p):
            size = os.path.getsize(p)
            changed.append(f'{f}={size}B')
    
    # 检查 final_answer
    final_path = os.path.join(IO_DIR, 'final_answer.txt')
    if os.path.exists(final_path) and os.path.getsize(final_path) > 0:
        final_content = open(final_path, encoding='utf-8').read().strip()
        if final_content:
            print(f'\n  [发现] final_answer.txt: {final_content[:100]}')
            found_final = True
            break
    
    # 检查 response.txt 是否被清空
    resp_path = os.path.join(IO_DIR, 'response.txt')
    resp_size = os.path.getsize(resp_path) if os.path.exists(resp_path) else 0
    if resp_size == 0 and 'response.txt=0B' not in changed:
        print(f'  [t+{int(time.time()-t0):2d}s] response.txt 被清空（REPL 正在处理）')
    
    if int(time.time() - t0) % 5 == 0:
        print(f'  [t+{int(time.time()-t0):2d}s] {", ".join(changed)}')
    
    time.sleep(0.5)

print(f'  结束时间:', time.strftime('%H:%M:%S'))

# === 最终状态 ===
print('\n[最终状态]')
show_io()

if found_final:
    print('\n' + '=' * 60)
    print('测试成功！')
    print('=' * 60)
else:
    print('\n[警告] 未找到 final_answer.txt')
    print('REPL 可能还需要更长时间，或者有问题')
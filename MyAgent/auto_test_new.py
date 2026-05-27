"""
MyAgent UI 自动化 - 修复版（使用新发现的控件位置）
====================================================
新启动的 MyAgent UI 控件位置与旧的不同
"""
import time, json, subprocess, urllib.request, os
from pywinauto import Application
import pywinauto.keyboard as kb

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'
IO_DIR = rf'{MYAGENT_DIR}\io'


def get_api_key():
    result = subprocess.run(
        ['powershell', '-Command', "[Environment]::GetEnvironmentVariable('MINIMAX_API_KEY', 'User')"],
        capture_output=True, text=True, encoding='utf-8'
    )
    return result.stdout.strip()

API_KEY = get_api_key()


def find_myagent():
    from pywinauto import findwindows
    windows = findwindows.find_windows(title_re='MyAgent.*')
    # 返回第一个窗口
    return windows[0] if windows else None


def connect_ui():
    hwnd = find_myagent()
    if not hwnd:
        return None
    app = Application(backend='win32').connect(handle=hwnd)
    return app.window(handle=hwnd)


def find_controls_by_pos(win):
    """通过坐标位置找到关键控件（基于新发现的布局）"""
    controls = {}
    for c in win.children():
        try:
            r = c.rectangle()
            x, y = r.left, r.top
            # 任务输入框：左侧，T≈178-334
            if 120 < x < 300 and 170 < y < 340:
                controls['task_input'] = c
            # 开始任务按钮：左侧，T≈342
            elif 120 < x < 300 and 340 < y < 420:
                controls['start_btn'] = c
            # Response 文本区：右侧，T≈950
            elif 900 < x < 1100 and 900 < y < 1570:
                controls['response_input'] = c
            # 粘贴&提交按钮：右侧，T≈1566
            elif 900 < x < 1100 and 1540 < y < 1640:
                controls['submit_btn'] = c
            # 新发现：复制prompt按钮
            elif 900 < x < 1100 and 800 < y < 900:
                controls['copy_prompt_btn'] = c
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


def get_session_final():
    session_file = os.path.join(IO_DIR, 'session.json')
    if os.path.exists(session_file) and os.path.getsize(session_file) > 0:
        try:
            data = json.loads(open(session_file, encoding='utf-8').read())
            turns = data.get('turns', [])
            for turn in reversed(turns):
                if 'final_answer' in turn and turn['final_answer']:
                    return turn['final_answer']
        except:
            pass
    return None


def wait_for_final_answer(old_session_size, timeout=30):
    session_file = os.path.join(IO_DIR, 'session.json')
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(session_file):
            size = os.path.getsize(session_file)
            if size > old_session_size:
                final = get_session_final()
                if final:
                    return final
        time.sleep(0.5)
    return None


print('=' * 60)
print('MyAgent UI 自动化 - 新控件位置')
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
if len(controls) < 4:
    print('  [警告] 控件不全')

clean_io()
print('[清空] io/')

# 步骤1：输入任务
print('\n[步骤1] 输入任务...')
task_input = controls.get('task_input')
if task_input:
    ui_paste(task_input, '请计算 1+1 等于几')
    print('  输入完成')
else:
    print('  [失败] 任务输入框未找到')
    exit(1)

# 步骤2：点击开始
print('[步骤2] 点击开始任务...')
start_btn = controls.get('start_btn')
if start_btn:
    click_btn(start_btn)
    print('  已点击')
else:
    print('  [失败] 开始按钮未找到')
    exit(1)

# 步骤3：等待 prompt
print('[步骤3] 等待 prompt 生成...')
prompt_path = os.path.join(IO_DIR, 'prompt.txt')
for i in range(20):
    time.sleep(1)
    if os.path.exists(prompt_path) and os.path.getsize(prompt_path) > 100:
        print(f'  {i+1}秒后 prompt 就绪')
        break

prompt = open(prompt_path, encoding='utf-8').read().strip()
print(f'  prompt 长度: {len(prompt)} chars')

# 步骤4：调用 LLM
print('\n[步骤4] 调用 LLM...')
result = call_llm(prompt)
if not result:
    print('  [失败] LLM 调用失败')
    exit(1)

action = result.get('action', '?')
print(f'  action={action}')
print(f'  answer={result.get("answer", "")[:80]}')

response_json = json.dumps(result, ensure_ascii=False)

# 步骤5：写 response.txt
print('\n[步骤5] 写 response.txt...')
open(os.path.join(IO_DIR, 'response.txt'), 'w', encoding='utf-8').write(response_json)
print(f'  已写入 {len(response_json)} chars')

# 记录 session.json 大小
session_file = os.path.join(IO_DIR, 'session.json')
old_session_size = os.path.getsize(session_file) if os.path.exists(session_file) else 0

# 步骤6：粘贴到 UI
print('[步骤6] 粘贴到 UI...')
resp_input = controls.get('response_input')
if resp_input:
    ui_paste(resp_input, response_json)
    time.sleep(0.5)
    print('  粘贴完成')
else:
    print('  [失败] response 文本区未找到')
    exit(1)

# 步骤7：点击提交
print('[步骤7] 点击提交...')
submit_btn = controls.get('submit_btn')
if submit_btn:
    click_btn(submit_btn)
    print('  已点击')
else:
    print('  [失败] 提交按钮未找到')
    exit(1)

# 步骤8：等待 REPL 处理
print('\n[步骤8] 轮询 session.json 等待 final_answer (20s)...')
print(f'  初始 session.json 大小: {old_session_size}')
final = wait_for_final_answer(old_session_size, timeout=20)

if final:
    print(f'\n[成功] final_answer: {final[:200]}')
    print('=' * 60)
    print('自动化测试成功！')
    print('=' * 60)
else:
    print('\n[警告] 未找到 final_answer')
    final_in_session = get_session_final()
    if final_in_session:
        print(f'[发现] session.json 中有 final_answer: {final_in_session[:100]}')
    else:
        print('[未发现] session.json 中也没有 final_answer')
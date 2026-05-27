"""
MyAgent UI 自动化 - 最终修复版
==============================
发现：REPL 处理完成后，结果保存在 session.json，不写 final_answer.txt
所以检查 final_answer.txt 永远等不到，要改检查 session.json

流程：
1. 输入任务 + 开始 -> prompt.txt 生成
2. 写 response.txt + 粘贴到 UI + 点击提交
3. 轮询检查 session.json 是否包含 "final_answer" 字段
4. 读到 final_answer 说明 REPL 处理完成
"""
import time, json, subprocess, urllib.request, os
from pywinauto import Application
import pywinauto.keyboard as kb

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'
IO_DIR = rf'{MYAGENT_DIR}\io'

# 从本地读取 API key，不硬编码
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


def get_session_final():
    """从 session.json 读取最新一条 final_answer"""
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


def wait_for_final_answer(old_session_size, timeout=20):
    """等待 session.json 出现 final_answer"""
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


def show_io(label=''):
    if label:
        print(f'  [{label}]')
    for f in ['input.txt', 'prompt.txt', 'response.txt']:
        p = os.path.join(IO_DIR, f)
        if os.path.exists(p):
            size = os.path.getsize(p)
            content = open(p, encoding='utf-8').read().strip()[:80] if size > 0 else ''
            print(f'    {f}: {size}B | {content}')
        else:
            print(f'    {f}: (不存在)')


print('=' * 60)
print('MyAgent UI 自动化 - 修复 final_answer 检测')
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

clean_io()
print('[清空] io/')

# 步骤1：输入任务
print('\n[步骤1] 输入任务...')
ui_paste(controls['task_input'], '请计算 1+1 等于几')
print('  输入完成')

# 步骤2：点击开始
print('[步骤2] 点击开始任务...')
click_btn(controls['start_btn'])
print('  已点击')

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
ui_paste(controls['response_input'], response_json)
time.sleep(0.5)
print('  粘贴完成')

# 步骤7：点击提交
print('[步骤7] 点击提交...')
click_btn(controls['submit_btn'])
print('  已点击')

# 步骤8：等待 REPL 处理（用 session.json 检测）
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
    show_io('最终状态')
    final_in_session = get_session_final()
    if final_in_session:
        print(f'[发现] session.json 中有 final_answer: {final_in_session[:100]}')
    else:
        print('[未发现] session.json 中也没有 final_answer')
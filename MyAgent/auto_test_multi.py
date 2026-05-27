"""
MyAgent UI 自动化 - 多轮循环版
===============================
API key 仅用于本地测试，不出现在主程序中

流程：
1. 输入任务 + 开始任务 → 生成 prompt.txt
2. 调用 LLM（action 可能=tool_call 或 final）
3. 写 response.txt + 粘贴到 UI + 点击提交
4. 等待 REPL 处理（检查 prompt.txt 是否有变化）
5. 重复直到 final_answer.txt 出现
"""
import time, json, subprocess, urllib.request, os, re
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


def wait_for_new_prompt(old_prompt_len, timeout=20):
    """等待 prompt.txt 有新内容（长度变化）"""
    prompt_path = os.path.join(IO_DIR, 'prompt.txt')
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(prompt_path):
            size = os.path.getsize(prompt_path)
            if size > old_prompt_len + 100:
                content = open(prompt_path, encoding='utf-8').read().strip()
                if content:
                    return content
        time.sleep(1)
    return None


def show_io(label=''):
    if label:
        print(f'  [{label}]')
    for f in ['input.txt', 'prompt.txt', 'response.txt', 'final_answer.txt']:
        p = os.path.join(IO_DIR, f)
        if os.path.exists(p):
            size = os.path.getsize(p)
            content = open(p, encoding='utf-8').read().strip()[:80] if size > 0 else ''
            print(f'    {f}: {size}B | {content}')


# ============ 主流程 ============

print('=' * 60)
print('MyAgent UI 自动化 - 多轮循环版')
print('=' * 60)

# 连接 UI
print('[连接] MyAgent UI...')
win = connect_ui()
if not win:
    print('  [失败] 未找到 MyAgent UI')
    exit(1)
print('  连接成功')

# 清空 io
clean_io()
print('[清空] io/')

# 通过位置找控件
controls = find_controls_by_pos(win)
print(f'  找到控件: {list(controls.keys())}')

# ========== 步骤1：输入任务 ==========
print('\n[步骤1] 输入任务...')
task_input = controls.get('task_input')
if not task_input:
    print('  [失败] 任务输入框未找到')
    exit(1)
ui_paste(task_input, '请计算 1+1 等于几')
print('  输入完成')

# ========== 步骤2：点击开始任务 ==========
print('[步骤2] 点击开始任务...')
start_btn = controls.get('start_btn')
if start_btn:
    click_btn(start_btn)
    print('  已点击')

# ========== 步骤3：等待第一轮 prompt 生成 ==========
print('[步骤3] 等待 prompt 生成...')
prompt_path = os.path.join(IO_DIR, 'prompt.txt')
for i in range(20):
    time.sleep(1)
    if os.path.exists(prompt_path) and os.path.getsize(prompt_path) > 100:
        print(f'  {i+1}秒后 prompt 就绪')
        break

prompt = open(prompt_path, encoding='utf-8').read().strip()
print(f'  prompt 长度: {len(prompt)} chars')

# ========== 多轮循环 ==========
current_prompt = prompt
last_prompt_len = len(prompt)
max_turns = 20

for turn in range(1, max_turns + 1):
    print(f'\n=== Turn {turn} ===')
    
    # 调用 LLM
    print('[LLM] 调用...')
    result = call_llm(current_prompt)
    if not result:
        print('  [失败] LLM 调用失败')
        break
    
    action = result.get('action', '?')
    print(f'  action={action}')
    if result.get('answer'):
        print(f'  answer={result.get("answer", "")[:80]}')
    if result.get('think'):
        print(f'  think={result.get("think", "")[:80]}')
    
    # 构造 response JSON
    response_json = json.dumps(result, ensure_ascii=False)
    
    # 写 response.txt
    open(os.path.join(IO_DIR, 'response.txt'), 'w', encoding='utf-8').write(response_json)
    print(f'  已写入 response.txt ({len(response_json)} chars)')
    
    # 粘贴到 UI
    print('[UI] 粘贴 response...')
    resp_input = controls.get('response_input')
    if resp_input:
        ui_paste(resp_input, response_json)
        time.sleep(0.5)
    
    # 点击提交
    print('[UI] 点击提交...')
    submit_btn = controls.get('submit_btn')
    if submit_btn:
        click_btn(submit_btn)
    
    # 等待 REPL 处理
    print('[等待] REPL 处理 (8s)...')
    time.sleep(8)
    
    # 检查 final_answer
    final_path = os.path.join(IO_DIR, 'final_answer.txt')
    if os.path.exists(final_path) and os.path.getsize(final_path) > 0:
        final_content = open(final_path, encoding='utf-8').read().strip()
        if final_content:
            print(f'\n[完成] final_answer: {final_content[:200]}')
            print('=' * 60)
            print('自动化测试成功！')
            print('=' * 60)
            exit(0)
    
    # 检查 response.txt 是否被读取（应该被清空）
    resp_path = os.path.join(IO_DIR, 'response.txt')
    resp_size = os.path.getsize(resp_path) if os.path.exists(resp_path) else 0
    if resp_size == 0:
        print('  [REPL] response.txt 已读取，继续')
    else:
        print(f'  [REPL] response.txt 仍有 {resp_size}B')
    
    # 等待新 prompt
    print('[等待] 新 prompt...')
    new_prompt = wait_for_new_prompt(last_prompt_len, timeout=15)
    
    if new_prompt:
        current_prompt = new_prompt
        last_prompt_len = len(current_prompt)
        print(f'  [REPL] 新 prompt ({len(current_prompt)} chars)，继续 Turn {turn + 1}')
    else:
        print('  [REPL] 未生成新 prompt')
        # 检查 prompt.txt 当前内容
        current_prompt = open(prompt_path, encoding='utf-8').read().strip()
        if current_prompt and len(current_prompt) > last_prompt_len:
            last_prompt_len = len(current_prompt)
            print(f'  [更新] prompt 长度={last_prompt_len}')
        else:
            print('  [结束] 无法继续')
            break

print('\n[超时] 达到最大轮次')
show_io('最终状态')
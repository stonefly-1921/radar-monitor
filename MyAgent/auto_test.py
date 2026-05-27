"""
MyAgent UI 自动化 - 完整测试
=============================
API key 内置在代码里，不再每次询问

流程：
1. 连接 UI（自动找窗口）
2. 输入任务到左侧任务输入框
3. 点击开始任务
4. 等待 prompt 生成（io/prompt.txt）
5. 调用 LLM 获取 response
6. 粘贴 response 到右侧 response 文本区
7. 点击粘贴&提交
8. 等待 REPL 处理，检查 final_answer.txt

控件通过坐标位置识别（不再用硬编码 HWND）：
- 任务输入框：左侧中间区域（L~236, T~242）
- 开始任务按钮：L=236, T=360
- Response 文本区：右侧中间（L~1042, T~968）
- 粘贴&提交按钮：L=1042, T=1584
"""
import time, json, subprocess, urllib.request, os
from pywinauto import Application
import pywinauto.keyboard as kb

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'
IO_DIR = rf'{MYAGENT_DIR}\io'
API_KEY = 'sk-cp-8BE1wiUugd-zZzIv4Zog8jluRsfL2Esdl6E3d1NudNSXMgaHEvqYySyJpN-UWfJ1B3SHtuc7lFWYqabiiz_VK-seQm-p4U50gFRDHbXJSvc0Dvvcl6XNqh4'


def find_myagent():
    """找到 MyAgent UI 的窗口 HWND"""
    from pywinauto import findwindows
    windows = findwindows.find_windows(title_re='MyAgent.*')
    return windows[0] if windows else None


def connect_ui():
    """连接到 MyAgent UI 窗口"""
    hwnd = find_myagent()
    if not hwnd:
        return None
    app = Application(backend='win32').connect(handle=hwnd)
    return app.window(handle=hwnd)


def find_controls_by_pos(win):
    """通过坐标位置找到关键控件"""
    controls = {}
    for c in win.children():
        try:
            r = c.rectangle()
            x, y = r.left, r.top
            # 任务输入框：左侧，T≈242
            if 200 < x < 300 and 200 < y < 300:
                controls['task_input'] = c
            # 开始任务按钮：左侧，T≈360
            elif 200 < x < 300 and 340 < y < 380:
                controls['start_btn'] = c
            # Response 文本区：右侧，T≈968
            elif 900 < x < 1100 and 900 < y < 1050:
                controls['response_input'] = c
            # 粘贴&提交按钮：右侧，T≈1584
            elif 900 < x < 1100 and 1550 < y < 1620:
                controls['submit_btn'] = c
        except:
            pass
    return controls


def ui_paste(ctrl, text):
    """粘贴文本到控件"""
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
    """调用 LLM"""
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


# ============ 主流程 ============

print('=' * 60)
print('MyAgent UI 自动化测试')
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
if len(controls) < 4:
    print('  [警告] 控件不全')

# ========== 步骤1：输入任务 ==========
print('\n[步骤1] 输入任务...')
task_input = controls.get('task_input')
if task_input:
    ui_paste(task_input, '请计算 1+1 等于几')
    print('  输入完成')
else:
    print('  [失败] 任务输入框未找到')
    exit(1)

# ========== 步骤2：点击开始任务 ==========
print('[步骤2] 点击开始任务...')
start_btn = controls.get('start_btn')
if start_btn:
    click_btn(start_btn)
    print('  已点击')
else:
    print('  [失败] 开始按钮未找到')
    exit(1)

# ========== 步骤3：等待 prompt 生成 ==========
print('[步骤3] 等待 prompt 生成...')
prompt_path = os.path.join(IO_DIR, 'prompt.txt')
for i in range(20):
    time.sleep(1)
    if os.path.exists(prompt_path) and os.path.getsize(prompt_path) > 100:
        print(f'  {i+1}秒后 prompt 就绪')
        break

prompt = open(prompt_path, encoding='utf-8').read().strip()
print(f'  prompt 长度: {len(prompt)} chars')

# ========== 步骤4：调用 LLM ==========
print('\n[步骤4] 调用 LLM...')
result = call_llm(prompt)
if not result:
    print('  [失败] LLM 调用失败')
    exit(1)

action = result.get('action', '?')
print(f'  action={action}')
print(f'  answer={result.get("answer", "")[:50]}')

# 写入 response.txt
response_json = json.dumps(result, ensure_ascii=False)
open(os.path.join(IO_DIR, 'response.txt'), 'w', encoding='utf-8').write(response_json)
print(f'  已写入 response.txt: {len(response_json)} chars')

# ========== 步骤5：粘贴到 response 文本区 ==========
print('\n[步骤5] 粘贴 response 到 UI...')
resp_input = controls.get('response_input')
if resp_input:
    ui_paste(resp_input, response_json)
    time.sleep(1)
    print('  粘贴完成')
else:
    print('  [失败] response 文本区未找到')
    exit(1)

# ========== 步骤6：点击提交 ==========
print('[步骤6] 点击「粘贴&提交」按钮...')
submit_btn = controls.get('submit_btn')
if submit_btn:
    click_btn(submit_btn)
    print('  已点击')
else:
    print('  [失败] 提交按钮未找到')
    exit(1)

# ========== 步骤7：等待 REPL 处理 ==========
print('\n[步骤7] 等待 REPL 处理 (15s)...')
time.sleep(15)

# ========== 步骤8：检查结果 ==========
print('\n[步骤8] 检查结果:')
show_io()

print('\n' + '=' * 60)
print('完成')
print('=' * 60)
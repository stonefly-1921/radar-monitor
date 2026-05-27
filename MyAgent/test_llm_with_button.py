"""完整测试：LLM + 点击提交按钮"""
import sys, os, time, json, subprocess, urllib.request
from pywinauto import Application
import pywinauto.keyboard as kb

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'
IO_DIR = os.path.join(MYAGENT_DIR, 'io')


def get_api_key():
    result = subprocess.run(
        ['powershell', '-Command', '[Environment]::GetEnvironmentVariable("MINIMAX_API_KEY", "User")'],
        capture_output=True, text=True, encoding='utf-8'
    )
    return result.stdout.strip()


def get_win():
    app = Application(backend='win32').connect(process=18012)
    return app.window(title='MyAgent v2.1')


def find(hwnd):
    win = get_win()
    for c in win.children():
        if c.handle == hwnd:
            return c
    return None


def ui_paste(hwnd, text):
    ctrl = find(hwnd)
    if not ctrl:
        return False
    ctrl.click_input()
    time.sleep(0.3)
    kb.send_keys('^a')
    time.sleep(0.1)
    kb.send_keys('{DELETE}')
    time.sleep(0.1)
    
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


def show_io():
    print('[IO 状态]')
    for f in ['input.txt', 'prompt.txt', 'response.txt', 'final_answer.txt']:
        p = os.path.join(IO_DIR, f)
        if os.path.exists(p):
            size = os.path.getsize(p)
            content = open(p, encoding='utf-8').read().strip()[:80] if size > 0 else ''
            print(f'  {f}: {size}B | {content}')
        else:
            print(f'  {f}: (不存在)')


print('='*60)
print('LLM + 按钮触发 REPL 测试')
print('='*60)

# 清空
for f in ['response.txt', 'final_answer.txt']:
    p = os.path.join(IO_DIR, f)
    if os.path.exists(p):
        open(p, 'w', encoding='utf-8').write('')
print('[清空] response.txt, final_answer.txt')

# 读 prompt.txt
prompt_path = os.path.join(IO_DIR, 'prompt.txt')
prompt = ''
if os.path.exists(prompt_path) and os.path.getsize(prompt_path) > 0:
    prompt = open(prompt_path, encoding='utf-8').read().strip()
print(f'[Prompt] 长度={len(prompt)}')

# 调用 LLM
print('[LLM] 调用...')
api_key = get_api_key()
url = 'https://api.minimaxi.com/anthropic/v1/messages'
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json',
    'anthropic-version': '2023-06-01',
}
payload = {
    'model': 'MiniMax-M2.7',
    'messages': [{'role': 'user', 'content': prompt}],
    'max_tokens': 8192,
    'temperature': 0.7
}
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode('utf-8'),
    headers=headers,
    method='POST'
)
result_data = None
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        for item in result.get('content', []):
            if item.get('type') == 'text':
                text = item.get('text', '').strip()
                if text:
                    try:
                        result_data = json.loads(text)
                    except:
                        result_data = {'action': 'final', 'answer': text}
except Exception as e:
    print(f'[LLM] 错误: {e}')
    sys.exit(1)

print(f'[LLM] action={result_data.get("action", "?")}, answer={result_data.get("answer", "")[:50]}')

# 写 response.txt
response_json = json.dumps(result_data, ensure_ascii=False)
resp_path = os.path.join(IO_DIR, 'response.txt')
open(resp_path, 'w', encoding='utf-8').write(response_json)
print(f'[写文件] response.txt = {len(response_json)} chars')

# 粘贴到 UI response 区
print('[UI] 粘贴 response 到 UI...')
ui_paste(28838998, response_json)
time.sleep(1)
print('  粘贴完成')

# 点击提交按钮
print('[UI] 点击粘贴&提交按钮...')
click_btn(15273062)
print('  已点击')

# 等待 REPL 处理
print('[等待] 15秒...')
time.sleep(15)

# 检查结果
print('[结果]')
show_io()
print('[完成]')
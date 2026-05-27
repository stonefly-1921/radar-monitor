"""MyAgent UI 自动化 - 单轮验证"""
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

def call_llm(prompt_text: str) -> dict:
    api_key = get_api_key()
    url = 'https://api.minimaxi.com/anthropic/v1/messages'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'anthropic-version': '2023-06-01',
    }
    payload = {
        'model': 'MiniMax-M2.7',
        'messages': [{'role': 'user', 'content': prompt_text}],
        'max_tokens': 8192,
        'temperature': 0.7
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        for item in result.get('content', []):
            if item.get('type') == 'text':
                text = item.get('text', '').strip()
                if text:
                    try:
                        return json.loads(text)
                    except:
                        return {'action': 'final', 'answer': text}

# 连接 UI
print('[连接]')
app = Application(backend='win32').connect(process=18012)
win = app.window(title='MyAgent v2.1')
print('  已连接')

# 清空 io/
for f in ['input.txt', 'response.txt', 'tool_result.json', 'final_answer.txt']:
    path = os.path.join(IO_DIR, f)
    if os.path.exists(path):
        open(path, 'w', encoding='utf-8').write('')
print('[清空] io/')

# 输入任务
print('[输入] 任务...')
task_input = [c for c in win.children() if c.handle == 13700270][0]
task_input.click_input()
time.sleep(0.3)
kb.send_keys('^a')
time.sleep(0.1)
kb.send_keys('{DELETE}')
task = '计算 1+1'
subprocess.run(['powershell', '-Command', f'Set-Clipboard -Value "{task}"'], capture_output=True)
time.sleep(0.3)
kb.send_keys('^v')
time.sleep(0.5)
print('  已输入')

# 点击开始任务
print('[开始]')
start_btn = [c for c in win.children() if c.handle == 265380][0]
start_btn.click_input()
print('  已点击')

# 等待 prompt
print('[等待] prompt...')
prompt_path = os.path.join(IO_DIR, 'prompt.txt')
for _ in range(20):
    time.sleep(1)
    if os.path.exists(prompt_path) and os.path.getsize(prompt_path) > 100:
        break
prompt = open(prompt_path, encoding='utf-8').read().strip()
print(f'  prompt 长度: {len(prompt)}')

# 调用 LLM
print('[LLM] 调用...')
result = call_llm(prompt)
print(f'  result: {result}')

# 粘贴 response
print('[粘贴] response...')
resp_input = [c for c in win.children() if c.handle == 28838998][0]
resp_input.click_input()
time.sleep(0.3)
kb.send_keys('^a')
time.sleep(0.1)
kb.send_keys('{DELETE}')
response_json = json.dumps(result, ensure_ascii=False)
subprocess.run(['powershell', '-Command', f'Set-Clipboard -Value "{response_json}"'], capture_output=True)
time.sleep(0.3)
kb.send_keys('^v')
time.sleep(0.5)
print('  已粘贴')

# 点击提交
print('[提交]')
submit_btn = [c for c in win.children() if c.handle == 15273062][0]
submit_btn.click_input()
print('  已点击')

# 等待
print('[等待] 10秒...')
time.sleep(10)

# 检查结果
print('[结果]')
show_io = lambda: None
for f in ['input.txt', 'prompt.txt', 'response.txt', 'tool_result.json', 'final_answer.txt']:
    path = os.path.join(IO_DIR, f)
    size = os.path.getsize(path) if os.path.exists(path) else 0
    content = open(path, encoding='utf-8').read().strip() if size > 0 else ''
    print(f'  {f}: {size} bytes | {content[:80]}')

print('\n完成')
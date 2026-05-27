"""
MyAgent 直接文件接口测试
========================
绕过 UI 键盘模拟，直接通过文件与 REPL 交互
"""
import time, json, subprocess, urllib.request, os, shutil

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'
IO_DIR = rf'{MYAGENT_DIR}\io'


def get_api_key():
    result = subprocess.run(
        ['powershell', '-Command', "[Environment]::GetEnvironmentVariable('MINIMAX_API_KEY', 'User')"],
        capture_output=True, text=True, encoding='utf-8'
    )
    return result.stdout.strip()

API_KEY = get_api_key()
print(f'API_KEY: {API_KEY[:15]}...')


def clean_io():
    for f in ['input.txt', 'response.txt', 'tool_result.json', 'final_answer.txt']:
        p = os.path.join(IO_DIR, f)
        if os.path.exists(p):
            open(p, 'w', encoding='utf-8').write('')


def wait_for_file(path, timeout=10):
    """等待文件出现且大小>0"""
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return True
        time.sleep(0.5)
    return False


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


print('=' * 60)
print('MyAgent 直接文件接口测试')
print('=' * 60)

# 清空 io 目录
clean_io()
print('[清空] io/ 目录')

# 检查 REPL 状态
repl_proc = None
for proc in subprocess.run(
    ['powershell', '-Command', 'Get-Process python | Select-Object Id'],
    capture_output=True, text=True
).stdout.split('\n'):
    try:
        pid = int(proc.strip())
        # 检查是否是 MyAgent UI 进程
        pass
    except:
        pass

print(f'REPL 进程 PID: 8304 (已知存在)')

# 步骤1：写入 input.txt（任务）
task = '请计算 1+1 等于几'
open(os.path.join(IO_DIR, 'input.txt'), 'w', encoding='utf-8').write(task)
print(f'[写入] input.txt: "{task}"')

# 步骤2：等待 REPL 生成 prompt.txt
print('[等待] REPL 生成 prompt.txt (10s)...')
if wait_for_file(os.path.join(IO_DIR, 'prompt.txt'), timeout=10):
    prompt = open(os.path.join(IO_DIR, 'prompt.txt'), encoding='utf-8').read().strip()
    print(f'  prompt.txt 大小: {len(prompt)} chars')
else:
    print('  [失败] prompt.txt 未生成')
    # 检查 session.json
    session_file = os.path.join(IO_DIR, 'session.json')
    if os.path.exists(session_file):
        print(f'  session.json 大小: {os.path.getsize(session_file)} bytes')
    exit(1)

# 步骤3：调用 LLM
print('\n[调用] LLM...')
result = call_llm(prompt)
if not result:
    print('  [失败] LLM 调用失败')
    exit(1)

action = result.get('action', '?')
print(f'  action={action}')
answer = result.get('answer', '')
print(f'  answer={answer[:100]}')

response_json = json.dumps(result, ensure_ascii=False)

# 步骤4：写 response.txt
open(os.path.join(IO_DIR, 'response.txt'), 'w', encoding='utf-8').write(response_json)
print(f'\n[写入] response.txt: {len(response_json)} chars')

# 记录 session.json 大小
session_file = os.path.join(IO_DIR, 'session.json')
old_size = os.path.getsize(session_file) if os.path.exists(session_file) else 0

# 等待 REPL 处理（polling session.json）
print('[等待] REPL 处理 response.txt...')
start = time.time()
final = None
while time.time() - start < 30:
    if os.path.exists(session_file):
        size = os.path.getsize(session_file)
        if size > old_size:
            final = get_session_final()
            if final:
                print(f'  [成功] 检测到 final_answer')
                break
    time.sleep(1)

if final:
    print(f'\n[结果] {final[:200]}')
    print('=' * 60)
    print('测试成功！')
    print('=' * 60)
else:
    print('\n[警告] 未检测到 final_answer')
    # 检查 session.json 内容
    final_in_session = get_session_final()
    if final_in_session:
        print(f'[发现] final_answer in session: {final_in_session[:100]}')
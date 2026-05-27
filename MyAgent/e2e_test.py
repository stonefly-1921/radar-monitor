"""
MyAgent 端到端测试 - 最简版本
============================
"""
import time, json, subprocess, urllib.request, os

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'
IO_DIR = rf'{MYAGENT_DIR}\io'

API_KEY = subprocess.run(
    ['powershell', '-Command', "[Environment]::GetEnvironmentVariable('MINIMAX_API_KEY', 'User')"],
    capture_output=True, text=True, encoding='utf-8'
).stdout.strip()
print(f'API_KEY: {API_KEY[:15]}...')

def clean_io():
    for f in ['input.txt', 'response.txt', 'tool_result.json', 'final_answer.txt']:
        p = os.path.join(IO_DIR, f)
        if os.path.exists(p):
            open(p, 'w', encoding='utf-8').write('')

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
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
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
print('MyAgent 端到端测试')
print('=' * 60)

# 1. 清空 io
clean_io()
print('[1] 清空 io')

# 2. 找 REPL 子进程
repl_pid = None
for proc in subprocess.run(['powershell', '-Command', 'Get-Process python | Select-Object Id'], capture_output=True, text=True).stdout.split('\n'):
    try:
        pid = int(proc.strip())
        if pid != os.getpid():
            try:
                import psutil
                p = psutil.Process(pid)
                cmdline = ' '.join(p.cmdline())
                if 'loop_v2.py' in cmdline:
                    repl_pid = pid
            except:
                pass
    except:
        pass

print(f'[2] REPL PID: {repl_pid}')

# 3. 直接给 REPL 发 stdin newline，触发它读取 input.txt
# 由于无法直接写 /proc/PID/fd/0，改用 notify 机制
# 写入 input.txt 后，通过某种方式触发 REPL

# 4. 写入 input.txt
task = '请计算 1+1 等于几'
open(os.path.join(IO_DIR, 'input.txt'), 'w', encoding='utf-8').write(task)
print(f'[3] 写入 input.txt: "{task}"')

# 5. 等待 REPL 处理（polling）
print('[4] 等待 REPL 生成 prompt.txt (10s)...')
start = time.time()
found = False
while time.time() - start < 10:
    prompt_file = os.path.join(IO_DIR, 'prompt.txt')
    if os.path.exists(prompt_file) and os.path.getsize(prompt_file) > 0:
        prompt = open(prompt_file, encoding='utf-8').read().strip()
        print(f'  prompt.txt 大小: {len(prompt)} chars')
        found = True
        break
    time.sleep(1)

if not found:
    # 检查 input.txt 是否还在
    input_content = open(os.path.join(IO_DIR, 'input.txt'), encoding='utf-8').read()
    print(f'  [失败] input.txt 内容: "{input_content}"')
    # 检查 session.json 大小是否变化
    session_size = os.path.getsize(os.path.join(IO_DIR, 'session.json'))
    print(f'  session.json 大小: {session_size}')
    print('\n[问题] REPL 没有监听 input.txt 文件变化')
    print('  可能原因: stdin 不是管道模式，REPL 依赖 stdin newline 触发读取')
    exit(1)

# 6. 调用 LLM
print('\n[5] 调用 LLM...')
result = call_llm(prompt)
if not result:
    print('  [失败] LLM 调用失败')
    exit(1)

print(f'  action={result.get("action")}')
print(f'  answer={result.get("answer", "")[:80]}')

response_json = json.dumps(result, ensure_ascii=False)

# 7. 写 response.txt
open(os.path.join(IO_DIR, 'response.txt'), 'w', encoding='utf-8').write(response_json)
print(f'\n[6] 写入 response.txt: {len(response_json)} chars')

# 记录 session.json 大小
session_file = os.path.join(IO_DIR, 'session.json')
old_size = os.path.getsize(session_file)

# 8. 等待 REPL 处理（polling session.json）
print('\n[7] 等待 REPL 处理 response.txt (30s)...')
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
    final_in_session = get_session_final()
    if final_in_session:
        print(f'[发现] final_answer in session: {final_in_session[:100]}')
"""
深入调试 REPL 行为 - 追踪每个文件读写
"""
import sys, os, time, subprocess, threading

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'
IO_DIR = os.path.join(MYAGENT_DIR, 'io')
API_KEY = subprocess.run(
    ['powershell', '-Command', "[Environment]::GetEnvironmentVariable('MINIMAX_API_KEY', 'User')"],
    capture_output=True, text=True, encoding='utf-8'
).stdout.strip()

def show_io(label=''):
    if label:
        print(f'  === {label} ===')
    for f in ['input.txt', 'prompt.txt', 'response.txt', 'final_answer.txt']:
        p = os.path.join(IO_DIR, f)
        if os.path.exists(p):
            size = os.path.getsize(p)
            content = open(p, encoding='utf-8').read().strip()[:60] if size > 0 else ''
            print(f'    {f}: {size}B | {content}')
        else:
            print(f'    {f}: (不存在)')

# 清空 io/
for f in ['input.txt', 'response.txt', 'tool_result.json', 'final_answer.txt']:
    p = os.path.join(IO_DIR, f)
    if os.path.exists(p):
        open(p, 'w', encoding='utf-8').write('')

# 写任务
open(os.path.join(IO_DIR, 'input.txt'), 'w', encoding='utf-8').write('请计算 1+1 等于几')
print('[写] input.txt: 请计算 1+1 等于几')
show_io('写任务后')

# 启动 REPL
env = dict(os.environ)
env['PYTHONIOENCODING'] = 'utf-8'
env['MINIMAX_API_KEY'] = API_KEY

loop_v2 = os.path.join(MYAGENT_DIR, 'agent', 'loop_v2.py')
print('\n[启动] REPL subprocess...')
proc = subprocess.Popen(
    [sys.executable, str(loop_v2)],
    cwd=MYAGENT_DIR,
    env=env,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True, bufsize=1, encoding='utf-8'
)
print(f'  PID={proc.pid}')

outputs = []
def read_outputs():
    for line in iter(proc.stdout.readline, ''):
        if line:
            outputs.append(line.rstrip())
            if len(outputs) <= 25:
                print(f'  [REPL] {line.rstrip()}')

t = threading.Thread(target=read_outputs, daemon=True)
t.start()

# 等待 REPL 启动
time.sleep(3)
print('\n[发送] newline to stdin...')
proc.stdin.write('\n')
proc.stdin.flush()

# 等待 REPL 处理
print('[等待] 15秒...')
time.sleep(15)

# 检查 io/
print('\n[IO 状态]')
show_io()

# 打印 REPL 输出
print(f'\n[REPL 输出] 共 {len(outputs)} 行:')
for line in outputs:
    print(f'  {line}')

# 杀掉 REPL
print('\n[杀掉 REPL]')
proc.kill()

# 现在写 response.txt 触发第二轮
print('\n=== 写 response.txt ===')
# 先读 prompt.txt
prompt = open(os.path.join(IO_DIR, 'prompt.txt'), encoding='utf-8').read().strip() if os.path.exists(os.path.join(IO_DIR, 'prompt.txt')) and os.path.getsize(os.path.join(IO_DIR, 'prompt.txt')) > 0 else ''
print(f'prompt.txt 大小: {len(prompt)} chars')

# 调用 LLM 获取 response
if prompt:
    import urllib.request, json
    url = 'https://api.minimaxi.com/anthropic/v1/messages'
    headers = {'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json', 'anthropic-version': '2023-06-01'}
    payload = {'model': 'MiniMax-M2.7', 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': 8192, 'temperature': 0.7}
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        for item in result.get('content', []):
            if item.get('type') == 'text':
                text = item.get('text', '').strip()
                if text:
                    response_json = text
                    try:
                        response_json = json.dumps(json.loads(text), ensure_ascii=False)
                    except:
                        response_json = json.dumps({'action': 'final', 'answer': text}, ensure_ascii=False)
                    open(os.path.join(IO_DIR, 'response.txt'), 'w', encoding='utf-8').write(response_json)
                    print(f'[写] response.txt: {response_json[:100]}...')

show_io('写 response.txt 后')

print('\n[完成]')
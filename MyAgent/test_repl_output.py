"""测试 REPL 并捕获其输出"""
import sys, os, time, subprocess, threading

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'
IO_DIR = os.path.join(MYAGENT_DIR, 'io')

api_key = subprocess.run(
    ['powershell', '-Command', '[Environment]::GetEnvironmentVariable("MINIMAX_API_KEY", "User")'],
    capture_output=True, text=True, encoding='utf-8'
).stdout.strip()

# 清空 io
for f in ['input.txt', 'response.txt', 'tool_result.json', 'final_answer.txt']:
    p = os.path.join(IO_DIR, f)
    if os.path.exists(p):
        open(p, 'w', encoding='utf-8').write('')

# 写任务
open(os.path.join(IO_DIR, 'input.txt'), 'w', encoding='utf-8').write('计算 1+1 等于几')

loop_v2 = os.path.join(MYAGENT_DIR, 'agent', 'loop_v2.py')
env = dict(os.environ)
env['PYTHONIOENCODING'] = 'utf-8'
env['MINIMAX_API_KEY'] = api_key

print('[启动] REPL...')
proc = subprocess.Popen(
    [sys.executable, str(loop_v2)],
    cwd=MYAGENT_DIR,
    env=env,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,  # 合并 stderr 到 stdout
    bufsize=1,  # 行缓冲
)
print(f'REPL PID: {proc.pid}')

# 用线程实时读取输出
outputs = []
def read_outputs():
    for line in iter(proc.stdout.readline, ''):
        if line:
            outputs.append(line.rstrip())

t = threading.Thread(target=read_outputs)
t.start()

# 发送 newline 触发
print('[发送] newline...')
proc.stdin.write(b'\n')
proc.stdin.flush()

# 等 8 秒
print('[等待] 8秒...')
time.sleep(8)

# 杀掉
proc.kill()
t.join(timeout=2)

print(f'[REPL 输出] 共 {len(outputs)} 行:')
for line in outputs[:20]:
    print(f'  {line}')

# 检查 io/
print('[IO 结果]')
for f in ['input.txt', 'prompt.txt', 'response.txt', 'final_answer.txt']:
    p = os.path.join(IO_DIR, f)
    if os.path.exists(p):
        size = os.path.getsize(p)
        content = open(p, encoding='utf-8').read().strip()[:100] if size > 0 else ''
        print(f'  {f}: {size}B | {content}')
    else:
        print(f'  {f}: (不存在)')
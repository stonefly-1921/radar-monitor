"""
直接单独运行 REPL（loop_v2.py），观察行为
============================================
不走 UI，直接通过 stdin/stdout 交互
"""
import sys, os, time, subprocess, threading

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'
IO_DIR = os.path.join(MYAGENT_DIR, 'io')
API_KEY = subprocess.run(
    ['powershell', '-Command', "[Environment]::GetEnvironmentVariable('MINIMAX_API_KEY', 'User')"],
    capture_output=True, text=True, encoding='utf-8'
).stdout.strip()

# 清空 io/
for f in ['input.txt', 'response.txt', 'tool_result.json', 'final_answer.txt']:
    p = os.path.join(IO_DIR, f)
    if os.path.exists(p):
        open(p, 'w', encoding='utf-8').write('')

# 写任务到 input.txt
open(os.path.join(IO_DIR, 'input.txt'), 'w', encoding='utf-8').write('请计算 1+1 等于几')
print('[写] input.txt: 请计算 1+1 等于几')

# 启动 REPL
env = dict(os.environ)
env['PYTHONIOENCODING'] = 'utf-8'
env['MINIMAX_API_KEY'] = API_KEY

loop_v2 = os.path.join(MYAGENT_DIR, 'agent', 'loop_v2.py')
print(f'[启动] REPL subprocess...')
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

# 读取 REPL 输出
outputs = []
def read_outputs():
    for line in iter(proc.stdout.readline, ''):
        if line:
            outputs.append(line.rstrip())

t = threading.Thread(target=read_outputs, daemon=True)
t.start()

# 等待 REPL 启动
time.sleep(3)

# 发送 newline 触发 input.txt 读取
print('[触发] 发送 newline...')
try:
    proc.stdin.write('\n')
    proc.stdin.flush()
    print('  已发送')
except Exception as e:
    print(f'  错误: {e}')

# 等待处理
print('[等待] 10秒...')
time.sleep(10)

# 打印 REPL 输出
print(f'\n[REPL 输出] 共 {len(outputs)} 行:')
for line in outputs[:30]:
    print(f'  {line}')

# 检查 io/
print('\n[IO 状态]')
for f in ['input.txt', 'prompt.txt', 'response.txt', 'final_answer.txt']:
    p = os.path.join(IO_DIR, f)
    if os.path.exists(p):
        size = os.path.getsize(p)
        content = open(p, encoding='utf-8').read().strip()[:80] if size > 0 else ''
        print(f'  {f}: {size}B | {content}')
    else:
        print(f'  {f}: (不存在)')

# 发送 quit 退出
print('\n[退出] 发送 quit...')
try:
    proc.stdin.write('quit\n')
    proc.stdin.flush()
    time.sleep(2)
    if proc.poll() is None:
        proc.kill()
except:
    pass

print('[完成]')
"""简单测试 REPL 子进程是否能独立运行"""
import sys, os, time, pathlib, subprocess

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'
IO_DIR = os.path.join(MYAGENT_DIR, 'io')

api_key_result = subprocess.run(
    ['powershell', '-Command', '[Environment]::GetEnvironmentVariable("MINIMAX_API_KEY", "User")'],
    capture_output=True, text=True, encoding='utf-8'
)
api_key = api_key_result.stdout.strip()
print(f'API key: {api_key[:15]}...' if api_key else 'API key: (empty)')

# 清空 io
for f in ['input.txt', 'response.txt', 'tool_result.json', 'final_answer.txt']:
    p = os.path.join(IO_DIR, f)
    if os.path.exists(p):
        open(p, 'w', encoding='utf-8').write('')
print('[清空] io/ done')

# 直接运行 loop_v2.py（无 UI 模式）
loop_v2 = os.path.join(MYAGENT_DIR, 'agent', 'loop_v2.py')
env = dict(os.environ)
env['PYTHONIOENCODING'] = 'utf-8'
env['MINIMAX_API_KEY'] = api_key

print(f'[启动] loop_v2.py...')
proc = subprocess.Popen(
    [sys.executable, str(loop_v2)],
    cwd=MYAGENT_DIR,
    env=env,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
print(f'REPL PID: {proc.pid}')

# 等 5 秒，看 io/ 变化
print('[等待] 5秒...')
time.sleep(5)

# 检查 io/
for f in ['input.txt', 'prompt.txt', 'response.txt', 'final_answer.txt']:
    p = os.path.join(IO_DIR, f)
    if os.path.exists(p):
        size = os.path.getsize(p)
        content = open(p, encoding='utf-8').read().strip()[:100] if size > 0 else ''
        print(f'{f}: {size}B | {content}')

# 写一个测试 input.txt 触发 REPL
print('[触发] 写 input.txt...')
open(os.path.join(IO_DIR, 'input.txt'), 'w', encoding='utf-8').write('测试任务：1+1=2')

# 发 newline 触发 REPL
print('[触发] 通知 REPL...')
try:
    proc.stdin.write('\n')
    proc.stdin.flush()
    print('  已发送 newline')
except Exception as e:
    print(f'  [错误] {e}')

# 等 3 秒
time.sleep(3)

# 再检查 io/
for f in ['input.txt', 'prompt.txt', 'response.txt', 'final_answer.txt']:
    p = os.path.join(IO_DIR, f)
    if os.path.exists(p):
        size = os.path.getsize(p)
        content = open(p, encoding='utf-8').read().strip()[:100] if size > 0 else ''
        print(f'{f}: {size}B | {content}')

# 杀掉 REPL
proc.kill()
print('[完成]')
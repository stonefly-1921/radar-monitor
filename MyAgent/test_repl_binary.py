"""测试 REPL stdin 字节写入"""
import sys, os, time, subprocess

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

# 写任务到 input.txt
open(os.path.join(IO_DIR, 'input.txt'), 'w', encoding='utf-8').write('计算 1+1 等于几')

# 启动 REPL（用二进制 stdin）
loop_v2 = os.path.join(MYAGENT_DIR, 'agent', 'loop_v2.py')
env = dict(os.environ)
env['PYTHONIOENCODING'] = 'utf-8'
env['MINIMAX_API_KEY'] = api_key

print('[启动] REPL (stdin=binary)...')
proc = subprocess.Popen(
    [sys.executable, str(loop_v2)],
    cwd=MYAGENT_DIR,
    env=env,
    stdin=subprocess.PIPE,  # 默认二进制模式
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
print(f'REPL PID: {proc.pid}')

# 等 REPL 启动
time.sleep(3)

# 发送 newline（用 bytes）
print('[发送] newline to REPL stdin...')
proc.stdin.write(b'\n')
proc.stdin.flush()

# 等待处理
print('[等待] 5秒...')
time.sleep(5)

# 检查 io/
print('[结果]')
for f in ['input.txt', 'prompt.txt', 'response.txt', 'final_answer.txt']:
    p = os.path.join(IO_DIR, f)
    if os.path.exists(p):
        size = os.path.getsize(p)
        content = open(p, encoding='utf-8').read().strip()[:100] if size > 0 else ''
        print(f'  {f}: {size}B | {content}')
    else:
        print(f'  {f}: (不存在)')

# 检查 REPL 进程
if proc.poll() is None:
    print('[REPL] 仍在运行')
    proc.kill()
else:
    stdout, stderr = proc.communicate()
    print(f'[REPL] 已退出')
    print(f'stdout: {stdout[:200]}')
    print(f'stderr: {stderr[:200]}')
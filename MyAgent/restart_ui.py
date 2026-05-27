"""重启 MyAgent UI"""
import subprocess, psutil, time, os, sys

# 杀掉所有 MyAgent UI 进程
print('[杀掉] MyAgent UI 进程...')
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if proc.info['name'] == 'python.exe' and proc.info['cmdline']:
            cmdline = ' '.join(proc.info['cmdline'])
            if 'ui.py' in cmdline and 'MyAgent' in cmdline:
                print(f'  杀掉 PID={proc.info["pid"]}')
                proc.kill()
    except Exception as e:
        print(f'  错误: {e}')

time.sleep(3)

# 读取 API key
api_key = subprocess.run(
    ['powershell', '-Command', "[Environment]::GetEnvironmentVariable('MINIMAX_API_KEY', 'User')"],
    capture_output=True, text=True, encoding='utf-8'
).stdout.strip()

# 启动 MyAgent UI
print('[启动] MyAgent UI...')
env = dict(os.environ)
env['MINIMAX_API_KEY'] = api_key
env['PYTHONIOENCODING'] = 'utf-8'

proc = subprocess.Popen(
    [sys.executable, 'C:\\Users\\15041\\.openclaw\\workspace\\MyAgent\\agent\\ui.py'],
    cwd='C:\\Users\\15041\\.openclaw\\workspace\\MyAgent',
    env=env,
)
print(f'  PID={proc.pid}')

time.sleep(5)

# 检查
print('[检查] REPL 子进程...')
try:
    p = psutil.Process(proc.pid)
    children = p.children(recursive=True)
    for child in children:
        try:
            if 'loop_v2.py' in ' '.join(child.cmdline()):
                env = child.environ()
                key = env.get('MINIMAX_API_KEY', '')
                if key:
                    print(f'  REPL PID={child.pid} API key 有效: {key[:10]}...')
                else:
                    print(f'  REPL PID={child.pid} API key: (空)')
        except Exception as e:
            print(f'  子进程检查错误: {e}')
except Exception as e:
    print(f'  检查错误: {e}')

print('[完成]')
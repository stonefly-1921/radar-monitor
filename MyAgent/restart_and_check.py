"""关闭所有 MyAgent UI 进程，然后启动一个新的"""
import psutil
import subprocess
import time

# 关闭所有 MyAgent UI 进程
print('[关闭] 查找并关闭 MyAgent UI...')
myagent_pids = []
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if proc.info['name'] == 'python.exe' and proc.info['cmdline']:
            cmdline = ' '.join(proc.info['cmdline'])
            if 'ui.py' in cmdline and 'MyAgent' in cmdline:
                print(f'  找到: PID={proc.info["pid"]} cmdline={cmdline}')
                myagent_pids.append(proc.info['pid'])
                proc.kill()
    except Exception as e:
        print(f'  错误: {e}')

print(f'已关闭 {len(myagent_pids)} 个进程')
time.sleep(2)

# 启动一个新的 MyAgent UI
print('[启动] 启动 MyAgent UI...')
api_key = subprocess.run(
    ['powershell', '-Command', "[Environment]::GetEnvironmentVariable('MINIMAX_API_KEY', 'User')"],
    capture_output=True, text=True, encoding='utf-8'
).stdout.strip()
print(f'API key: {"有效" if api_key else "(空)"}')

env = dict(subprocess.os.environ)
env['MINIMAX_API_KEY'] = api_key
env['PYTHONIOENCODING'] = 'utf-8'

proc = subprocess.Popen(
    ['D:\\anaconda3\\python.exe', 'C:\\Users\\15041\\.openclaw\\workspace\\MyAgent\\agent\\ui.py'],
    cwd='C:\\Users\\15041\\.openclaw\\workspace\\MyAgent',
    env=env,
)
print(f'启动 PID={proc.pid}')
time.sleep(5)

# 检查是否启动成功
print('[检查] 新进程...')
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if p.info['pid'] == proc.pid:
            print(f'  进程: {p.info}')
            children = p.children(recursive=True)
            for child in children:
                print(f'  子进程: PID={child.pid} name={child.name()}')
                try:
                    env = child.environ()
                    key = env.get('MINIMAX_API_KEY', '')
                    print(f'    MINIMAX_API_KEY: {"有效" if key else "(空)"}')
                    if key:
                        print(f'    前15字符: {key[:15]}...')
                except:
                    pass
    except:
        pass

print('[完成]')
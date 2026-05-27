"""带调试输出的 REPL 测试"""
import sys, os, time, json, subprocess, urllib.request, threading

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'
IO_DIR = os.path.join(MYAGENT_DIR, 'io')

# API key
api_key = subprocess.run(
    ['powershell', '-Command', '[Environment]::GetEnvironmentVariable("MINIMAX_API_KEY", "User")'],
    capture_output=True, text=True, encoding='utf-8'
).stdout.strip()
print(f'API key: {api_key[:15]}...' if api_key else 'API key: (empty)')

# 清空
for f in ['response.txt', 'final_answer.txt']:
    p = os.path.join(IO_DIR, f)
    if os.path.exists(p):
        open(p, 'w', encoding='utf-8').write('')

# 找 REPL 子进程
repl_pid = None
result = subprocess.run(
    ['powershell', '-Command', 
     'Get-WmiObject Win32_Process | Where-Object { $_.ParentProcessId -eq 18012 } | Select-Object ProcessId'],
    capture_output=True, text=True, encoding='utf-8'
)
for line in result.stdout.split('\n'):
    line = line.strip()
    if line.isdigit():
        repl_pid = int(line)
        break

print(f'REPL PID: {repl_pid}')

# 用 Python 的 psutil 替代 WMI（更可靠）
try:
    import psutil
    parent = psutil.Process(18012)
    children = parent.children(recursive=True)
    print(f'UI 子进程: {[c.pid for c in children]}')
    
    for child in children:
        print(f'  PID={child.pid} name={child.name()} cmdline={child.cmdline()}')
        # 检查环境变量
        try:
            env = child.environ()
            print(f'    MINIMAX_API_KEY in env: {"MINIMAX_API_KEY" in env}')
            if 'MINIMAX_API_KEY' in env:
                print(f'    MINIMAX_API_KEY value: {env["MINIMAX_API_KEY"][:10]}...')
        except:
            pass
except ImportError:
    print('psutil 未安装，使用 WMI 结果')
    print(f'REPL PID from WMI: {repl_pid}')

print('[完成]')
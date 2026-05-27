"""给正在运行的 MyAgent UI 进程的 REPL 子进程注入 API key"""
import subprocess
import psutil
import time

print('[检查] User 环境变量...')
api_key = subprocess.run(
    ['powershell', '-Command', '[Environment]::GetEnvironmentVariable("MINIMAX_API_KEY", "User")'],
    capture_output=True, text=True, encoding='utf-8'
).stdout.strip()
print(f'User MINIMAX_API_KEY: {"有效" if api_key else "(空)"}')
if api_key:
    print(f'前15字符: {api_key[:15]}...')

print('\n[查找] 三个 MyAgent UI 进程...')
myagent_pids = [3764, 18772, 28912]
for pid in myagent_pids:
    try:
        proc = psutil.Process(pid)
        print(f'\nPID={pid}: {proc.cmdline()}')
        children = proc.children(recursive=True)
        for child in children:
            if 'loop_v2.py' in ' '.join(child.cmdline()):
                print(f'  REPL 子进程: PID={child.pid}')
                try:
                    env = child.environ()
                    current_key = env.get('MINIMAX_API_KEY', '')
                    print(f'    当前 MINIMAX_API_KEY: {"有效" if current_key else "(空)"}')
                    
                    # 尝试通过 psutil 设置环境变量（可能需要管理员权限）
                    # 这是 Linux/macOS 的方法，Windows 不支持
                    # child.environ()['MINIMAX_API_KEY'] = api_key
                    
                    print(f'    [注意] 无法通过 psutil 修改另一个进程的环境变量')
                    print(f'    需要重启 UI 才能让 REPL 获得正确的 API key')
                except Exception as e:
                    print(f'    错误: {e}')
    except Exception as e:
        print(f'PID={pid} 错误: {e}')

print('\n[结论]')
print('REPL 子进程的 API key 为空，因为 UI 启动时没有正确继承 User 环境变量')
print('需要关闭并重新启动 MyAgent UI（从同一个 Python 进程启动，确保环境变量被读取）')
print('或者修改 ui.py，在 _start_repl_subprocess 中显式读取 User 环境变量')

print('\n[建议修复方案]')
print('修改 ui.py 的 _start_repl_subprocess 方法，在启动 REPL 前读取 User 环境变量:')
print('  env["MINIMAX_API_KEY"] = subprocess.run(...)')

print('\n[完成]')
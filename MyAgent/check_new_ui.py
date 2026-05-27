"""检查新启动的 MyAgent UI 的 REPL 环境变量"""
import subprocess
import psutil
import time

# 等待新进程启动
time.sleep(2)

# 找 MyAgent v2 进程（窗口标题是 "MyAgent v2" 不是 "MyAgent v2.1"）
print('[查找] MyAgent UI 进程...')
myagent_pids = []
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if proc.info['name'] == 'python.exe' and proc.info['cmdline']:
            cmdline = ' '.join(proc.info['cmdline'])
            if 'ui.py' in cmdline:
                print(f'  PID={proc.info["pid"]}: {cmdline}')
                myagent_pids.append(proc.info['pid'])
    except:
        pass

for pid in myagent_pids:
    print(f'\n[检查] PID={pid} 的子进程...')
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            print(f'  子进程: PID={child.pid} name={child.name()}')
            try:
                env = child.environ()
                api_key = env.get('MINIMAX_API_KEY', '(未设置)')
                print(f'    MINIMAX_API_KEY: {"有效" if api_key else "(空)"}')
                if api_key:
                    print(f'    前15字符: {api_key[:15]}...')
            except Exception as e:
                print(f'    环境变量读取失败: {e}')
    except Exception as e:
        print(f'  错误: {e}')

print('\n[完成]')
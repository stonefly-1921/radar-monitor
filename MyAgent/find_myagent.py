"""找当前运行的 MyAgent UI 进程"""
import psutil

print('[查找] MyAgent UI 进程...')
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if proc.info['name'] == 'python.exe' and proc.info['cmdline']:
            cmdline = ' '.join(proc.info['cmdline'])
            if 'ui.py' in cmdline and 'MyAgent' in cmdline:
                print(f'  PID={proc.info["pid"]}: {cmdline}')
                # 检查子进程
                children = proc.children(recursive=True)
                for child in children:
                    print(f'    子进程: PID={child.pid} name={child.name()}')
                    try:
                        env = child.environ()
                        key = env.get('MINIMAX_API_KEY', '')
                        print(f'      MINIMAX_API_KEY: {"有效" if key else "(空)"}')
                        if key:
                            print(f'      前15字符: {key[:15]}...')
                    except:
                        pass
    except:
        pass

print('[完成]')
"""
启动 MyAgent UI 并确保 REPL 子进程运行
"""
import sys, os, time, pathlib, subprocess

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'

def get_api_key():
    result = subprocess.run(
        ['powershell', '-Command', '[Environment]::GetEnvironmentVariable("MINIMAX_API_KEY", "User")'],
        capture_output=True, text=True, encoding='utf-8'
    )
    return result.stdout.strip()

def check_ui_process():
    """检查 MyAgent UI 是否在跑"""
    result = subprocess.run(
        ['powershell', '-Command', 'Get-Process -Name python | Where-Object {$_.MainWindowTitle -eq "MyAgent v2.1"} | Select-Object Id'],
        capture_output=True, text=True, encoding='utf-8'
    )
    lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip() and 'Id' not in l]
    if lines:
        try:
            return int(lines[-1].strip())
        except:
            pass
    return None

def start_repl_manually():
    """手动启动 REPL 子进程（loop_v2.py）"""
    api_key = get_api_key()
    loop_v2 = os.path.join(MYAGENT_DIR, 'agent', 'loop_v2.py')
    
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['MINIMAX_API_KEY'] = api_key
    
    print(f'[启动] REPL 子进程...')
    print(f'  API key: {api_key[:10]}...' if api_key else '  API key: (空)')
    
    proc = subprocess.Popen(
        [sys.executable, loop_v2],
        cwd=MYAGENT_DIR,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    print(f'  PID: {proc.pid}')
    return proc

def test_repl_communication(repl_proc):
    """测试 REPL 是否正常通信"""
    print('[测试] REPL 通信...')
    try:
        # 发一个测试信号
        repl_proc.stdin.write('\n')
        repl_proc.stdin.flush()
        
        # 等一下
        time.sleep(2)
        
        # 检查进程是否还活着
        if repl_proc.poll() is not None:
            stdout, stderr = repl_proc.communicate(timeout=1)
            print(f'  [错误] REPL 已退出')
            print(f'  stdout: {stdout[:200]}')
            print(f'  stderr: {stderr[:200]}')
            return False
        
        print('  REPL 运行中')
        return True
    except Exception as e:
        print(f'  [错误] {e}')
        return False

def main():
    print('='*60)
    print('MyAgent UI + REPL 启动器')
    print('='*60)
    
    # 检查 UI
    pid = check_ui_process()
    if pid:
        print(f'[MyAgent UI] PID={pid} 已在运行')
    else:
        print('[错误] MyAgent UI 未运行，请先启动')
        return
    
    # 启动 REPL 子进程
    repl_proc = start_repl_manually()
    
    # 测试
    ok = test_repl_communication(repl_proc)
    
    if ok:
        print('\n[成功] REPL 子进程已启动')
        print(f'  PID: {repl_proc.pid}')
        print('\n现在可以用自动化脚本操作 MyAgent UI 了')
    else:
        print('\n[失败] REPL 子进程启动失败')
        repl_proc.kill()

if __name__ == '__main__':
    main()
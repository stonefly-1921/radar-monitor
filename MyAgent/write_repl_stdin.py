"""
通过 Windows API 直接给 REPL stdin 写入数据
"""
import subprocess, psutil, time, os

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'
IO_DIR = rf'{MYAGENT_DIR}\io'

# REPL PID
REPL_PID = 8304

# 使用 psutil 打开 REPL 的 stdin 并写入
print('通过 psutil 打开 REPL stdin...')
try:
    proc = psutil.Process(REPL_PID)
    
    # 尝试使用 psutil 的 stdin 渠道
    # psutil 没有直接写 stdin 的方法，但我们可以尝试用 windows API
    import ctypes
    from ctypes import wintypes
    
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    
    # 获取 REPL 进程的 stdin handle
    # HANDLE hStdInput = GetStdHandle(STD_INPUT_HANDLE);
    STD_INPUT_HANDLE = -10
    
    # 对于子进程，GetStdHandle 返回的是继承的 stdin
    # 但我们直接用 Popen 的 stdin 渠道会更好
    
    # 尝试打开 REPL 进程的 stdout
    # 这种方法可能不行，因为我们不是用 DEBUG_PROCESS 启动的
    
    print(f'REPL PID={REPL_PID}, status={proc.status()}')
    print(f'REPL stdin: {proc.io_counters() if hasattr(proc, "io_counters") else "unknown"}')
    
    # 尝试用 powershell 直接写
    print('\n用 powershell 写 stdin...')
    cmd = f'''
    $proc = Get-Process -Id {REPL_PID}
    # 无法直接访问子进程的 stdin，因为它是继承的管道
    # 正确的方法是通过父进程（UI）写管道
    '''
    print(cmd)
    
except Exception as e:
    print(f'错误: {e}')

# 换一种方法：通过 UI 的 _notify_repl 机制
# UI 在 _on_start_task 末尾调用 _notify_repl()，向 REPL stdin 写入换行符
# 我们可以模拟这个行为 - 写 input.txt 后，触发某个机制

# 实际上，问题在于：REPL 的 stdin 是从 UI 继承的
# UI 在 start 后会写 input.txt，然后调用 _notify_repl()
# _notify_repl 写 '\n' 到 REPL 的 stdin，REPL 的 input() 调用因此返回

# 但是当我们直接写 input.txt 时，没有 UI 来调用 _notify_repl
# REPL 卡在 input() 调用上，等待 stdin 有数据

print('\n检查 input.txt...')
input_file = os.path.join(IO_DIR, 'input.txt')
print(f'input.txt 大小: {os.path.getsize(input_file)}')
print(f'input.txt 内容: {open(input_file, encoding="utf-8").read()}')

# 尝试：给 REPL 发送 Ctrl+C 然后重新启动？
# 或者：重启 REPL 进程并使用不同的 stdin 模式？

# 最简单的方法：重启 UI，让 UI 正常启动 REPL
print('\n请手动重启 MyAgent UI，然后测试...')
print('或者，我们可以写一个新的 REPL 启动脚本，使用不同的 stdin 处理方式')
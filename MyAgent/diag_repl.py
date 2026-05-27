"""
深入诊断 REPL 为什么没有读取 input.txt
"""
import subprocess, psutil, time, os

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'
IO_DIR = rf'{MYAGENT_DIR}\io'

# 检查 REPL 子进程
REPL_PID = 30552

print('=== 诊断 REPL 进程 ===')
try:
    proc = psutil.Process(REPL_PID)
    print(f'REPL PID: {REPL_PID}')
    print(f'REPL status: {proc.status()}')
    print(f'REPL cmdline: {proc.cmdline()}')
    
    # 检查 stdin 是否可用
    try:
        stdin_fd = proc.uents()[0].fd
        print(f'REPL stdin fd: {stdin_fd}')
    except Exception as e:
        print(f'REPL stdin fd error: {e}')
    
    # 检查环境变量
    env = proc.environ()
    print(f'ENV PYTHONIOENCODING: {env.get("PYTHONIOENCODING", "NOT SET")}')
    print(f'ENV MINIMAX_API_KEY: {env.get("MINIMAX_API_KEY", "NOT SET")[:15]}...')
    
    # 检查 io 目录的文件
    print(f'\nio 目录文件:')
    for f in os.listdir(IO_DIR):
        size = os.path.getsize(os.path.join(IO_DIR, f))
        print(f'  {f}: {size} bytes')
    
    # 检查 stdin.isatty()
    # 通过一个小脚本来测试 REPL 的 stdin 状态
    print('\n测试 REPL stdin.isatty()...')
    test_script = '''
import sys
print(f"stdin.isatty() = {sys.stdin.isatty()}", flush=True)
print(f"stdin.fileno() = {sys.stdin.fileno()}", flush=True)
import os
try:
    print(f"os.isatty(0) = {os.isatty(0)}", flush=True)
except:
    print("os.isatty(0) error", flush=True)
'''
    
    # 这个测试无法直接执行，因为我们不是 REPL 的父进程
    # 但我们可以通过另一种方式检查
    
except Exception as e:
    print(f'错误: {e}')

# 关键发现：REPL 的 stdin 是管道，stdin.isatty() 返回 False
# 在这种模式下，如果 input.txt 有内容，会被读取
# 但我们的测试显示 input.txt 没有被读取

print('\n=== 关键问题 ===')
print('REPL stdin 是管道 (PIPE)，stdin.isatty() 返回 False')
print('在这种模式下，_wait_for_input 的逻辑是：')
print('1. 如果 input.txt 有内容 -> 读并返回')
print('2. 如果 input.txt 无内容 -> 跳过 input() (因为非交互) -> 继续等待文件')
print('')
print('但是，我们发现 input.txt 内容没有被读。')
print('可能原因：input.txt 在检查之前就被清空了？')
print('')
print('让我们检查 input.txt 被谁清空的...')

# 写 input.txt
test_content = 'test_from_diag'
with open(os.path.join(IO_DIR, 'input.txt'), 'w', encoding='utf-8') as f:
    f.write(test_content)
print(f'\n写入 input.txt: "{test_content}"')

# 等待 3s
time.sleep(3)

# 检查 input.txt 是否还在
if os.path.exists(os.path.join(IO_DIR, 'input.txt')):
    content = open(os.path.join(IO_DIR, 'input.txt'), encoding='utf-8').read()
    print(f'input.txt 当前内容: "{content}"')
else:
    print('input.txt 不存在')

# 检查 prompt.txt 是否出现
prompt_file = os.path.join(IO_DIR, 'prompt.txt')
if os.path.exists(prompt_file) and os.path.getsize(prompt_file) > 0:
    print(f'prompt.txt 大小: {os.path.getsize(prompt_file)}')
else:
    print('prompt.txt 未出现')
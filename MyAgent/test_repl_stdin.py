"""直接测试 REPL 的 input.txt 监听"""
import subprocess, psutil, time, os

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'
IO_DIR = rf'{MYAGENT_DIR}\io'

# 检查 REPL 子进程 stdin
proc = psutil.Process(8304)
print(f'REPL stdin: {proc.is_open() if hasattr(proc, "is_open") else "unknown"}')
print(f'REPL status: {proc.status()}')

# 读取 REPL 的 stdout fd
try:
    import resource
    r = resource.getrlimit(resource.RLIMIT_NOFILE)
    print(f'FD limit: soft={r[0]}, hard={r[1]}')
except:
    pass

# 检查 stdin's fd
stdin_fd = proc.uents()._fields[0].fd if hasattr(proc, 'uents') else None
print(f'stdin fd: {stdin_fd}')

# 直接给 REPL 发 stdin，看 REPL 是否响应
print('\n给 REPL 发 stdin newline...')
try:
    with open(f'/proc/{8304}/fd/0', 'w') as f:
        f.write('\n')
        print('  写入成功')
except Exception as e:
    print(f'  错误: {e}')

# 检查 prompt.txt 是否出现
time.sleep(3)
prompt_file = os.path.join(IO_DIR, 'prompt.txt')
if os.path.exists(prompt_file):
    size = os.path.getsize(prompt_file)
    print(f'prompt.txt 大小: {size}')
    if size > 0:
        content = open(prompt_file, encoding='utf-8').read().strip()
        print(f'内容: {content[:100]}...')
else:
    print('prompt.txt 未出现')
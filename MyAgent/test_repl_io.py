"""通过 Windows 调试方法检查 REPL stdin"""
import subprocess, psutil, time, os

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'
IO_DIR = rf'{MYAGENT_DIR}\io'

proc = psutil.Process(8304)

# 尝试读取 REPL 的 cmdline
print(f'REPL cmdline: {proc.cmdline()}')

# 尝试读取环境变量
env = proc.environ()
print(f'ENV MINIMAX_API_KEY: {env.get("MINIMAX_API_KEY", "NOT SET")[:15]}...')

# 检查 io 目录
print(f'\nio 目录: {IO_DIR}')
for f in os.listdir(IO_DIR):
    size = os.path.getsize(os.path.join(IO_DIR, f))
    print(f'  {f}: {size} bytes')

# 写 input.txt 看 REPL 是否响应
print('\n写入 test_input 到 input.txt...')
with open(os.path.join(IO_DIR, 'input.txt'), 'w', encoding='utf-8') as f:
    f.write('test_input')

# 等待 5s
print('等待 5s...')
time.sleep(5)

# 检查 prompt.txt
prompt_file = os.path.join(IO_DIR, 'prompt.txt')
if os.path.exists(prompt_file) and os.path.getsize(prompt_file) > 0:
    print(f'prompt.txt: {os.path.getsize(prompt_file)} bytes')
    content = open(prompt_file, encoding='utf-8').read().strip()
    print(f'内容: {content[:200]}')
else:
    print('prompt.txt 未出现')

# 检查 input.txt 是否被清空
input_content = open(os.path.join(IO_DIR, 'input.txt'), encoding='utf-8').read()
print(f'input.txt 当前内容: "{input_content}"')
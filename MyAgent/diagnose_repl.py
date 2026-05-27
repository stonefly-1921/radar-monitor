"""诊断 REPL 状态 - 检查 stdin 是否可写"""
import subprocess, psutil, time, os

REPL_PID = 25500  # REPL 子进程 PID

print('=' * 60)
print('REPL 诊断')
print('=' * 60)

try:
    repl = psutil.Process(REPL_PID)
    print(f'REPL 进程: PID={repl.pid}')
    print(f'  状态: {repl.status()}')
    print(f'  运行时间: {repl.create_time()}')
    
    # 检查 stdin/stdout 是否存在
    try:
        stdin_fd = repl.fd()  # 文件描述符列表
        print(f'  文件描述符数量: {len(stdin_fd)}')
        for fd in stdin_fd[:5]:
            print(f'    fd={fd}')
    except:
        print('  无法获取文件描述符')
    
    # 检查环境变量
    env = repl.environ()
    key = env.get('MINIMAX_API_KEY', '')
    print(f'  MINIMAX_API_KEY: {"有效" if key else "(空)"}')
    if key:
        print(f'    前15字符: {key[:15]}...')
    
    # 尝试通过 psutil 给 REPL 发信号
    print('\n[测试] 发送信号测试...')
    # 不发送任何东西，只是测试进程是否响应
    
    # 检查子进程
    children = repl.children()
    print(f'  REPL 的子进程: {len(children)}')
    for child in children:
        print(f'    PID={child.pid} name={child.name()}')
        
except psutil.NoSuchProcess:
    print(f'[错误] REPL 进程 {REPL_PID} 不存在')
except Exception as e:
    print(f'[错误] {e}')

# 检查 io/
print('\n[IO 状态]')
io_dir = r'C:\Users\15041\.openclaw\workspace\MyAgent\io'
for f in ['input.txt', 'prompt.txt', 'response.txt', 'tool_result.json', 'final_answer.txt']:
    p = os.path.join(io_dir, f)
    if os.path.exists(p):
        size = os.path.getsize(p)
        content = open(p, encoding='utf-8').read().strip()[:60] if size > 0 else ''
        print(f'  {f}: {size}B | {content}')
    else:
        print(f'  {f}: (不存在)')

print('\n[完成]')
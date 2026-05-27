"""
MyAgent UI REPL 环境变量问题分析

问题：REPL 子进程的 MINIMAX_API_KEY 环境变量可能为空

测试：确认 REPL 是否能用正确的 API key 调用 LLM

方案：
1. 直接 attach 到 REPL 进程的 stdin/stdout
2. 写入测试任务，验证 REPL 是否能正常处理

如果 REPL 的 API key 为空，它处理时会报 "API key 未配置" 错误
"""
import sys, os, time, subprocess, threading

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'
IO_DIR = os.path.join(MYAGENT_DIR, 'io')

print('='*60)
print('REPL 环境变量诊断')
print('='*60)

# 检查 REPL 的环境变量
try:
    import psutil
    repl_proc = psutil.Process(30408)
    env = repl_proc.environ()
    api_key_in_repl = env.get('MINIMAX_API_KEY', '(未设置)')
    print(f'REPL 的 MINIMAX_API_KEY: {api_key_in_repl[:20]}...' if len(api_key_in_repl) > 20 else f'REPL 的 MINIMAX_API_KEY: {api_key_in_repl}')
    
    # 检查系统环境变量
    system_key = os.environ.get('MINIMAX_API_KEY', '(未设置)')
    print(f'当前进程的 MINIMAX_API_KEY: {system_key[:20]}...' if len(system_key) > 20 else f'当前进程的 MINIMAX_API_KEY: {system_key}')
    
except Exception as e:
    print(f'检查失败: {e}')

# 尝试 attach 到 REPL 的 stdin/stdout
print('\n[Attach] 尝试 attach 到 REPL stdin/stdout...')

try:
    # 获取 REPL 的 stdin/stdout 文件描述符
    repl_proc = psutil.Process(30408)
    print(f'REPL 进程: PID={repl_proc.pid}, cmdline={repl_proc.cmdline()}')
    
    # 检查 stdin/stdout 是否可读写
    for conn in repl_proc.connections(kind='pipe'):
        print(f'  Pipe: {conn}')
        
except Exception as e:
    print(f'Attach 失败: {e}')

print('\n[结论]')
print('如果 REPL 的 API key 为空，REPL 内的 LLM 调用会失败')
print('这解释了为什么提交 response.txt 后 REPL 没有继续处理')
print('解决方案：重启 MyAgent UI（让 REPL 获取正确的 API key）')

print('\n[完成]')
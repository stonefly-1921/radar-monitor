"""检查 REPL 子进程"""
import subprocess, psutil, time

print('=== 检查 REPL 进程 ===')
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if proc.info['name'] == 'python.exe' and proc.info['cmdline']:
            cmdline = ' '.join(proc.info['cmdline'])
            if 'loop_v2.py' in cmdline:
                print(f'REPL PID={proc.info["pid"]}')
                print(f'  cmdline: {cmdline}')
                p = psutil.Process(proc.info['pid'])
                print(f'  parent: {p.parent().name()} PID={p.parent().pid}')
                # 查看子进程
                children = p.children(recursive=True)
                print(f'  children: {len(children)}')
                for child in children:
                    print(f'    child PID={child.pid} name={child.name()}')
    except Exception as e:
        print(f'错误: {e}')

print('=== 检查 session.json 状态 ===')
import json, os
session_file = r'C:\Users\15041\.openclaw\workspace\MyAgent\io\session.json'
if os.path.exists(session_file) and os.path.getsize(session_file) > 0:
    data = json.loads(open(session_file, encoding='utf-8').read())
    turns = data.get('turns', [])
    print(f'session.json: {len(turns)} turns')
    for t in turns[-3:]:
        print(f"  Turn {t['turn']}: final_answer={t.get('final_answer', '')[:50]}")
else:
    print('session.json 不存在或为空')
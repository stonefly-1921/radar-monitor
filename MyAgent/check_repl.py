"""检查 REPL 子进程状态"""
import subprocess
import time

# 检查进程 30408 的 stdin/stdout 是否可读
result = subprocess.run(['powershell', '-Command', 'Get-WmiObject Win32_Process -Filter "ProcessId=30408" | Select-Object ProcessId,CommandLine'], capture_output=True, text=True, encoding='utf-8')
print(result.stdout)
print(result.stderr)
"""通过 WMI 获取 MyAgent UI 的 REPL 子进程"""
import subprocess

# 使用 WMI 查询
result = subprocess.run(
    ['powershell', '-Command', 
     'Get-WmiObject Win32_Process | Where-Object { $_.ParentProcessId -eq 18012 } | Select-Object ProcessId, Name, CommandLine | Format-Table -AutoSize'],
    capture_output=True, text=True, encoding='utf-8'
)
print(result.stdout)
print(result.stderr)
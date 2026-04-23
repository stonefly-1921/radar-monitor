import subprocess
import sys
import os
import time

os.chdir(r'C:\Users\15041\Desktop\wechat-decrypt')

print('Starting decrypt...')
result = subprocess.run(
    [sys.executable, 'main.py', 'decrypt'],
    capture_output=True,
    timeout=300
)
print('Done, return code:', result.returncode)
print('STDOUT:', result.stdout.decode('utf-8', errors='replace')[:2000])

import subprocess
import sys
import os

os.chdir(r'C:\Users\15041\Desktop\wechat-decrypt')
print('Starting Web UI...')
proc = subprocess.Popen([sys.executable, 'main.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
print(f'PID: {proc.pid}')
import time
time.sleep(5)
print('Waiting for server to start...')
stdout, stderr = proc.communicate(timeout=10)
print('STDOUT:', stdout.decode('utf-8', errors='replace')[:2000])
print('STDERR:', stderr.decode('utf-8', errors='replace')[:1000])

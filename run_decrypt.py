import subprocess
import sys
import os

os.chdir(r'C:\Users\15041\Desktop\wechat-decrypt')
result = subprocess.run([sys.executable, 'main.py', 'decrypt'], capture_output=True)
print('Return code:', result.returncode)
print('STDOUT:', result.stdout.decode('utf-8', errors='replace')[:3000])
print('STDERR:', result.stderr.decode('utf-8', errors='replace')[:2000])

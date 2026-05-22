import sys, time, ctypes
from PIL import ImageGrab
import subprocess
from pywinauto import Application
from pywinauto.keyboard import send_keys

user32 = ctypes.windll.user32

# Check if Qwen window exists
hwnd_test = 133298
title_len = user32.GetWindowTextLengthW(hwnd_test)
print('HWND 133298 title length:', title_len)

if title_len > 0:
    buf = ctypes.create_unicode_buffer(title_len + 1)
    n = user32.GetWindowTextW(hwnd_test, buf, title_len + 1)
    print('GetWindowTextW returned:', n, 'Title:', buf.value)
else:
    print('No title (window may be gone)')
    
# Also check what process 21024 is
print('Process 21024 exists:', end=' ')
try:
    import os
    os.kill(21024, 0)
    print('yes')
except:
    print('no')
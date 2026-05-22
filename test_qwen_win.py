import sys, time, ctypes
from PIL import ImageGrab

user32 = ctypes.windll.user32

# Check Qwen window at known HWND
hwnd = 133298
n = user32.GetWindowTextLengthW(hwnd)
if n <= 0:
    print('NO_WINDOW')
    sys.exit(1)

buf = ctypes.create_unicode_buffer(n + 1)
user32.GetWindowTextW(hwnd, buf, n + 1)
title = buf.value
print('Title:', title)

class RECT(ctypes.Structure):
    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]

r = RECT()
user32.GetWindowRect(hwnd, ctypes.byref(r))
L, T, R, B = r.left, r.top, r.right, r.bottom
print('Rect:', L, T, R, B)

# Restore if minimized
if user32.IsIconic(hwnd):
    user32.ShowWindow(hwnd, 9)
    time.sleep(1.0)
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    L, T, R, B = r.left, r.top, r.right, r.bottom

# Focus
user32.SetForegroundWindow(hwnd)
time.sleep(0.5)

# Click at bottom-center of window (input area)
w, h = R - L, B - T
cx = L + w // 2
cy = T + int(h * 0.88)

user32.SetCursorPos(cx, cy)
time.sleep(0.2)
user32.mouse_event(0x02, 0, 0, 0, 0)  # LBtn down
time.sleep(0.05)
user32.mouse_event(0x04, 0, 0, 0, 0)  # LBtn up
time.sleep(0.5)
print('Clicked input at', cx, cy)

# Send text via PowerShell SendKeys
text = 'Hello Qwen from MyAgent!'
import subprocess
subprocess.run([
    'powershell', '-ExecutionPolicy', 'Bypass', '-Command',
    'Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait("' + text + '")'
], capture_output=True, timeout=10)
time.sleep(0.3)
subprocess.run([
    'powershell', '-ExecutionPolicy', 'Bypass', '-Command',
    'Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")'
], capture_output=True, timeout=5)
print('Sent:', text)

# Wait
print('Waiting 6s...')
time.sleep(6)

# Screenshot
img = ImageGrab.grab(bbox=(L, T, R, B))
img.save('C:/Users/15041/.openclaw/workspace/qwen_test.png')
print('Screenshot saved:', img.size)
print('DONE')
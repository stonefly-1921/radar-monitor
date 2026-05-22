import ctypes, time, sys, subprocess
from PIL import ImageGrab

user32 = ctypes.windll.user32

class RECT(ctypes.Structure):
    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]

results = []
def callback(hwnd, _):
    if user32.IsWindowVisible(hwnd):
        n = user32.GetWindowTextLengthW(hwnd)
        if n > 0:
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            title = buf.value
            if title and '千问' in title:
                r = RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(r))
                results.append((hwnd, title, r.left, r.top, r.right, r.bottom))
    return True

user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(callback), 0)

if not results:
    print('Qwen not found')
    sys.exit(1)

hwnd, title, L, T, R, B = results[0]
w, h = R - L, B - T
print(f'Window: {L},{T},{R},{B} Size: {w}x{h}')

if user32.IsIconic(hwnd):
    user32.ShowWindow(hwnd, 9)
    time.sleep(1.0)
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    L, T, R, B = r.left, r.top, r.right, r.bottom

user32.SetForegroundWindow(hwnd)
time.sleep(0.5)

# Click at "向千问提问" text - based on analysis it's in the bottom-right area
# Normalized [916, 642] to [1000, 1000] in 0-1000 scale
# Window is 1440x852, so x = 922-1440, y = 775-852
# Try clicking at the text position: center around (960+1440)//2, (775+852)//2 = (1200, 813)
cx = 960
cy = 810
print(f'Clicking at ({cx}, {cy}) - "向千问提问" text area')
user32.SetCursorPos(cx, cy)
time.sleep(0.3)
user32.mouse_event(0x02, 0, 0, 0, 0)
time.sleep(0.05)
user32.mouse_event(0x04, 0, 0, 0, 0)
time.sleep(0.5)
print('Clicked')

# Now send keys
text = '你好千问，我是MyAgent测试'
subprocess.run([
    'powershell', '-ExecutionPolicy', 'Bypass', '-Command',
    'Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait("' + text + '")'
], capture_output=True, timeout=10)
print('Sent text via SendKeys')
time.sleep(0.3)

subprocess.run([
    'powershell', '-ExecutionPolicy', 'Bypass', '-Command',
    'Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")'
], capture_output=True, timeout=5)
print('Sent Enter')

# Wait for response
print('Waiting 8s...')
time.sleep(8)

# Screenshot
img = ImageGrab.grab(bbox=(L, T, R, B))
img.save('C:/Users/15041/.openclaw/workspace/qwen_result.png')
print('Screenshot saved')

print('DONE')
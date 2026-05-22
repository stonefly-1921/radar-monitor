import ctypes, time

user32 = ctypes.windll.user32

EnumWindows = user32.EnumWindows
GetWindowText = user32.GetWindowTextW
GetWindowRect = user32.GetWindowRect
IsWindowVisible = user32.IsWindowVisible
IsIconic = user32.IsIconic
ShowWindow = user32.ShowWindow
SetForegroundWindow = user32.SetForegroundWindow
SetCursorPos = user32.SetCursorPos
mouse_event = user32.mouse_event

L_click = 0x02
L_up = 0x04

# Find Qwen
windows = []
def callback(hwnd, lParam):
    if IsWindowVisible(hwnd):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            GetWindowText(hwnd, buf, length + 1)
            title = buf.value
            if '千问' in title:
                class RECT(ctypes.Structure):
                    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
                r = RECT()
                GetWindowRect(hwnd, ctypes.byref(r))
                windows.append((hwnd, title, r.left, r.top, r.right, r.bottom))
    return True

EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(callback), 0)

if not windows:
    print('Qwen not found!')
else:
    hwnd, title, L, T, R, B = windows[0]
    print(f'Found: {title} Rect:{L},{T},{R},{B}')
    
    # Restore if minimized
    if IsIconic(hwnd):
        ShowWindow(hwnd, 9)
        time.sleep(1.0)
        class RECT(ctypes.Structure):
            _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
        r = RECT()
        GetWindowRect(hwnd, ctypes.byref(r))
        L, T, R, B = r.left, r.top, r.right, r.bottom
        print(f'Restored rect: {L},{T},{R},{B}')
    
    # Focus
    SetForegroundWindow(hwnd)
    time.sleep(0.5)
    
    # Try clicking the center-bottom area where input usually is
    # Qwen UI: sidebar (left), main area (right), input at bottom
    w, h = R - L, B - T
    print(f'Window size: {w}x{h}')
    
    # Click center of window (should be in the chat area)
    cx = L + w // 2
    cy = T + int(h * 0.85)  # near bottom
    
    SetCursorPos(cx, cy)
    time.sleep(0.2)
    mouse_event(L_click, 0, 0, 0, 0)
    time.sleep(0.05)
    mouse_event(L_up, 0, 0, 0, 0)
    print(f'Clicked at screen ({cx},{cy})')
    time.sleep(0.5)
    
    # Send test message
    import subprocess
    text = 'Hi Qwen, this is MyAgent test'
    r = subprocess.run([
        'powershell', '-ExecutionPolicy', 'Bypass', '-Command',
        f'Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait("{text}")'
    ], capture_output=True, timeout=10)
    print(f'SendKeys: {r.returncode}')
    
    time.sleep(0.3)
    r = subprocess.run([
        'powershell', '-ExecutionPolicy', 'Bypass', '-Command',
        'Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")'
    ], capture_output=True, timeout=5)
    print(f'Enter: {r.returncode}')
    
    print('MESSAGE_SENT')
    
    time.sleep(8)
    
    from PIL import ImageGrab
    img = ImageGrab.grab(bbox=(L, T, R, B))
    img.save('C:/Users/15041/.openclaw/workspace/qwen_result.png')
    print(f'SCREENSHOT:{img.size}')
    print('DONE')
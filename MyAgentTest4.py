import ctypes, time

user32 = ctypes.windll.user32

# Find Qwen window
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
    print('Qwen window not found!')
else:
    hwnd, title, L, T, R, B = windows[0]
    print(f'Found: {title} HWND:{hwnd} Rect:{L},{T},{R},{B}')
    
    # Restore if minimized
    if IsIconic(hwnd):
        print('Window is minimized, restoring...')
        ShowWindow(hwnd, 9)  # SW_RESTORE = 9
        time.sleep(1.0)
        # Re-get rect after restore
        class RECT(ctypes.Structure):
            _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
        r = RECT()
        GetWindowRect(hwnd, ctypes.byref(r))
        L, T, R, B = r.left, r.top, r.right, r.bottom
        print(f'New rect after restore: {L},{T},{R},{B}')
    
    # Focus window
    SetForegroundWindow(hwnd)
    time.sleep(0.5)
    print('WINDOW_FOCUSED')
    
    # Click in the input area (approximate - 70% down from top, center horizontally)
    click_x = L + (R - L) // 2
    click_y = T + int((B - T) * 0.75)
    print(f'Clicking at {click_x},{click_y}')
    SetCursorPos(click_x, click_y)
    time.sleep(0.2)
    mouse_event(L_click, 0, 0, 0, 0)
    time.sleep(0.05)
    mouse_event(L_up, 0, 0, 0, 0)
    print('CLICK_DONE')
    
    time.sleep(0.3)
    
    # Send text via PowerShell SendKeys (no .ps1 extension issue)
    import subprocess
    text = 'Hi Qwen, this is MyAgent test'
    r = subprocess.run([
        'powershell', '-ExecutionPolicy', 'Bypass', '-Command',
        f'Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait("{text}")'
    ], capture_output=True, timeout=10)
    print(f'SendKeys result: {r.returncode}')
    
    time.sleep(0.5)
    r = subprocess.run([
        'powershell', '-ExecutionPolicy', 'Bypass', '-Command',
        'Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")'
    ], capture_output=True, timeout=5)
    print(f'Enter result: {r.returncode}')
    
    print('TEXT_SENT')
    
    # Wait for response
    time.sleep(5)
    
    # Screenshot
    from PIL import ImageGrab
    img = ImageGrab.grab(bbox=(L, T, R, B))
    img.save('C:/Users/15041/.openclaw/workspace/qwen_result.png')
    print(f'SCREENSHOT_SAVED:{img.size}')
    print('ALL_DONE')
import ctypes, time
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

if results:
    hwnd, title, L, T, R, B = results[0]
    print('Window:', L, T, R, B, 'Size:', R-L, 'x', B-T)
    
    # Screenshot
    img = ImageGrab.grab(bbox=(L, T, R, B))
    img.save('C:/Users/15041/.openclaw/workspace/qwen_input_test.png')
    print('Screenshot saved')
    
    # Try clicking at different positions to find input field
    # Let's try clicking at various heights to find the input box
    positions = [
        (L + (R-L)//2, T + int((B-T) * 0.85)),  # 85% down
        (L + (R-L)//2, T + int((B-T) * 0.90)),  # 90% down  
        (L + (R-L)//2, T + int((B-T) * 0.95)),  # 95% down
        (L + (R-L)//2, B - 50),  # 50px from bottom
        (L + (R-L)//2, B - 100),  # 100px from bottom
    ]
    
    # Restore and focus
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)
        time.sleep(1.0)
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        L, T, R, B = r.left, r.top, r.right, r.bottom
    
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)
    
    for i, (cx, cy) in enumerate(positions):
        print(f'Try {i+1}: clicking at ({cx}, {cy})')
        user32.SetCursorPos(cx, cy)
        time.sleep(0.2)
        user32.mouse_event(0x02, 0, 0, 0, 0)
        time.sleep(0.05)
        user32.mouse_event(0x04, 0, 0, 0, 0)
        time.sleep(1.0)
    
    print('Done trying positions')
else:
    print('Qwen not found')
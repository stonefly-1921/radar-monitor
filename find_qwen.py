import ctypes, time

user32 = ctypes.windll.user32

# EnumWindows to find Qwen window
EnumWindows = user32.EnumWindows
GetWindowText = user32.GetWindowTextW
GetWindowRect = user32.GetWindowRect
IsWindowVisible = user32.IsWindowVisible

windows = []

def callback(hwnd, lParam):
    if IsWindowVisible(hwnd):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            GetWindowText(hwnd, buf, length + 1)
            title = buf.value
            rect = ctypes.Structure
            class RECT(ctypes.Structure):
                _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
            r = RECT()
            GetWindowRect(hwnd, ctypes.byref(r))
            if '千问' in title or 'qianwen' in title.lower() or 'Qwen' in title:
                windows.append((hwnd, title, r.left, r.top, r.right, r.bottom))
    return True

EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(callback), 0)

for hwnd, title, L, T, R, B in windows:
    print(f'HWND:{hwnd} Title:{title} Rect:{L},{T},{R},{B}')
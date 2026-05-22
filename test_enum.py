import ctypes
user32 = ctypes.windll.user32
EnumWindows = user32.EnumWindows
GetWindowText = user32.GetWindowTextW
IsWindowVisible = user32.IsWindowVisible
GetWindowRect = user32.GetWindowRect

results = []

def callback(hwnd, lParam):
    if IsWindowVisible(hwnd):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            GetWindowText(hwnd, buf, length + 1)
            title = buf.value
            if title and ('千问' in title or 'qian' in title.lower()):
                class RECT(ctypes.Structure):
                    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
                r = RECT()
                GetWindowRect(hwnd, ctypes.byref(r))
                results.append((hwnd, title, r.left, r.top, r.right, r.bottom))
    return True

EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(callback), 0)

if results:
    for hwnd, title, L, T, R, B in results:
        print('HWND:' + str(hwnd) + ' Title:' + title + ' Rect:' + str(L) + ',' + str(T) + ',' + str(R) + ',' + str(B))
else:
    print('No Qwen windows found')
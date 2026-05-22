import ctypes
user32 = ctypes.windll.user32

results = []

def callback(hwnd, _):
    if user32.IsWindowVisible(hwnd):
        n = user32.GetWindowTextLengthW(hwnd)
        if n > 0:
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            title = buf.value
            if title and '千' in title:
                class RECT(ctypes.Structure):
                    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
                r = RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(r))
                results.append((hwnd, title, r.left, r.top, r.right, r.bottom))
    return True

user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(callback), 0)

if results:
    for hwnd, title, L, T, R, B in results:
        print(f'HWND:{hwnd} Title:{title} Rect:{L},{T},{R},{B}')
else:
    print('No windows with 千 found')
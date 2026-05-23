import win32gui
import win32con

hwnd = 1575860

children = []
def enum_child_cb(hwnd_child, results):
    if win32gui.IsWindowVisible(hwnd_child):
        title = win32gui.GetWindowText(hwnd_child)
        clsname = win32gui.GetClassName(hwnd_child)
        rect = win32gui.GetWindowRect(hwnd_child)
        results.append({
            'hwnd': hwnd_child,
            'title': title,
            'class': clsname,
            'rect': rect
        })

win32gui.EnumChildWindows(hwnd, enum_child_cb, children)
for c in children:
    print(f'  HWND={c["hwnd"]} class={c["class"]} title={repr(c["title"])} rect={c["rect"]}')
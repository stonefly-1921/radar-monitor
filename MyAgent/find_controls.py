"""重新发现 MyAgent UI 控件位置"""
from pywinauto import Application, findwindows

hwnds = findwindows.find_windows(title_re='MyAgent.*')
print(f'找到 {len(hwnds)} 个窗口')
for hwnd in hwnds:
    print(f'  HWND={hwnd}')
    app = Application(backend='win32').connect(handle=hwnd)
    win = app.window(handle=hwnd)
    print(f'  title={win.window_text()}')
    for c in win.children():
        try:
            r = c.rectangle()
            print(f'    HWND={c.handle} class={c.class_name} L={r.left},T={r.top},R={r.right},B={r.bottom}')
        except:
            pass
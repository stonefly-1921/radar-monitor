import pyautogui
import time
import win32gui
import win32con

hwnd = 1575860

# Bring to foreground
win32gui.SetForegroundWindow(hwnd)
time.sleep(0.5)

# Save full screenshot
pyautogui.screenshot('C:/Users/15041/.openclaw/workspace/qianwen_full.png')
print('Screenshot saved')

# Also find all visible elements using UI Automation
import ctypes
from ctypes.wintypes import HWND, RECT, POINT

OLECMDID_NEW = 0
OLECMDID_SAVE = 3

# Try to find input area by searching for text
try:
    # Use accessible object from UI Automation
    import pyhook
except:
    pass

# Try direct win32gui approach for Edit controls
windows = []
def enum_cb(hwnd, results):
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        cls = win32gui.GetClassName(hwnd)
        if cls in ['Edit', 'RICHEDIT', 'WebViewEdit', 'Chrome_RenderWidgetHostHWND']:
            rect = win32gui.GetWindowRect(hwnd)
            results.append({'hwnd': hwnd, 'class': cls, 'title': title, 'rect': rect})

win32gui.EnumChildWindows(hwnd, enum_cb, windows)
for w in windows:
    print(f'Found edit: HWND={w["hwnd"]} class={w["class"]} title={repr(w["title"])} rect={w["rect"]}')
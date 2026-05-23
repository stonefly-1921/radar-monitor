# Find Qianwen window's input area using Win32 API
import win32gui
import win32con
import win32ui
import ctypes
from ctypes.wintypes import HWND, RECT, POINT
import pyautogui
import time

hwnd = 1575860

# First, let's find all child elements including the WebView input
# Use UI Automation if available
try:
    import uiaAutomation
    print("UI Automation available")
except ImportError:
    print("UI Automation not available")

# Let's enumerate all child windows deeply
def get_all_children(hwnd_parent, depth=0, max_depth=5):
    if depth > max_depth:
        return []
    children = []
    def cb(hwnd_child, results):
        if win32gui.IsWindowVisible(hwnd_child):
            title = win32gui.GetWindowText(hwnd_child)
            cls = win32gui.GetClassName(hwnd_child)
            rect = win32gui.GetWindowRect(hwnd_child)
            style = win32gui.GetWindowLong(hwnd_child, win32con.GWL_STYLE)
            exstyle = win32gui.GetWindowLong(hwnd_child, win32con.GWL_EXSTYLE)
            results.append({
                'hwnd': hwnd_child,
                'title': title,
                'class': cls,
                'rect': rect,
                'style': style,
                'exstyle': exstyle
            })
            # Recurse
            get_all_children(hwnd_child, depth+1, max_depth)
    win32gui.EnumChildWindows(hwnd_parent, cb, children)
    return children

children = get_all_children(hwnd)
print(f"Found {len(children)} total child windows")
for c in children[:30]:
    print(f"  HWND={c['hwnd']} class={c['class'][:30]} title={repr(c['title'][:30])} rect={c['rect']}")

# Find the main content/edit area
for c in children:
    if c['class'] in ['Chrome_RenderWidgetHostHWND', 'RTF Edit Control', 'Internet Explorer_TridentL']:
        print(f"\nPotential input area: HWND={c['hwnd']} rect={c['rect']}")
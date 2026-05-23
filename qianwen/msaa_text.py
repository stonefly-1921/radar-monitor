# Try to get text from WebView using MSAA (Microsoft Active Accessibility)
import win32gui
import win32con
import win32accessibility
import comtypes
from comtypes.client import CoCreateInstance
from comtypes.automation import IDispatch
import time

hwnd = 1575860

# Focus window
win32gui.SetForegroundWindow(hwnd)
time.sleep(0.3)

# Use MSAA to get accessible object
try:
    acc_obj = win32accessibility.AccessibleObjectFromWindow(hwnd, win32con.OBJID_CLIENT)
    if acc_obj:
        print(f"Got accessible object: {acc_obj}")
        # Try to get children
        try:
            child_count = acc_obj.accChildCount
            print(f"Child count: {child_count}")
        except:
            pass
except Exception as e:
    print(f"MSAA failed: {e}")

# Try using shell.activex to get WebView content
try:
    from ctypes.windll import oleacc
    import comtypes.gen.MSHTML as MSHTML
    
    pAcc = win32accessibility.AccessibleObjectFromWindow(hwnd, win32con.OBJID_CLIENT)
    if pAcc:
        print(f"Got IDispatch: {pAcc}")
except Exception as e:
    print(f"ActiveX failed: {e}")

# Try GetFocusedClipBoardText using user32
import ctypes
user32 = ctypes.windll.user32

# WM_GETTEXT doesn't work for WebView
# Let's try to get text from the active window using SendMessage
def get_webview_text(hwnd):
    """Try to get text from WebView2 using various methods."""
    # Method 1: WM_GETTEXT with edit-like controls
    # WebView2 uses Edge WebView2, not standard edit controls
    # So WM_GETTEXT won't work directly
    
    # Method 2: Use IUIAutomation if available
    try:
        from ctypes.windll import oleacc
        from ctypes import POINTER, c_long
        
        # Get root accessible object
        pRoot = win32accessibility.AccessibleObjectFromWindow(hwnd, win32con.OBJID_WINDOW)
        if pRoot:
            print(f"Root accessible: {pRoot}")
            try:
                child = pRoot.accNavigate(win32con.NAVDIR_FIRSTCHILD)
                if child:
                    print(f"First child: {child}")
            except Exception as e:
                print(f"Navigate failed: {e}")
    except Exception as e:
        print(f"oleacc failed: {e}")

get_webview_text(hwnd)
import win32gui
import win32ui
import win32con
import ctypes
from PIL import Image
import pyautogui
import time

hwnd = 1575860

# Bring to foreground and get focus
win32gui.SetForegroundWindow(hwnd)
time.sleep(0.3)

# Get client area size
client_rect = win32gui.GetClientRect(hwnd)
w, h = client_rect[2], client_rect[3]
print(f'Client area: {w}x{h}')

# Get window DC
hwndDC = win32gui.GetWindowDC(hwnd)
mfcDC = win32ui.CreateDCFromHandle(hwndDC)
saveDC = mfcDC.CreateCompatibleDC()

# Create bitmap
saveBitMap = win32ui.CreateBitmap()
saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
saveDC.SelectObject(saveBitMap)

# Use PrintWindow from user32
user32 = ctypes.windll.user32
user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)  # 2 = client area only

# Convert to PIL image
bmpinfo = saveBitMap.GetInfo()
bmpstr = saveBitMap.GetBitmapBits(True)
img = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)
img.save('C:/Users/15041/.openclaw/workspace/qianwen_printwindow.png')
print(f'Saved PrintWindow capture: {img.size}')

win32gui.ReleaseDC(hwnd, hwndDC)
win32ui.DeleteDC(mfcDC)
win32ui.DeleteDC(saveDC)
import pyautogui
import time
import win32gui
import ctypes
from PIL import Image
import io
import base64

hwnd = 1575860

# Get window rect
rect = win32gui.GetWindowRect(hwnd)
print(f'Window rect: {rect}')  # (0, 0, 2880, 1704)

# Take full screenshot and crop to this window
img = pyautogui.screenshot()
# Crop to window bounds
window_img = img.crop((0, 0, 2880, 1704))
window_img.save('C:/Users/15041/.openclaw/workspace/qianwen_full_window.png')
print(f'Saved full window screenshot: {window_img.size}')

# Also save bottom section where input/response appears
bottom_img = img.crop((0, 1200, 2880, 1704))
bottom_img.save('C:/Users/15041/.openclaw/workspace/qianwen_bottom_section.png')
print(f'Saved bottom section: {bottom_img.size}')

# Save middle section where messages appear
mid_img = img.crop((0, 500, 2880, 1200))
mid_img.save('C:/Users/15041/.openclaw/workspace/qianwen_mid_section.png')
print(f'Saved mid section: {mid_img.size}')
"""
截取千问窗口的聊天区域，用 minimax vision 读取
"""
import pyautogui
import time
import win32gui
import os
import sys

hwnd = 1575860
win32gui.SetForegroundWindow(hwnd)
time.sleep(0.5)

# The WebView client area is (13, 56) to (2867, 1692) in window coords
# But since window starts at (0,0) on screen, that's the whole window
# Let's try to capture just the message area - upper 2/3 of window
img = pyautogui.screenshot()

# Save full window area (the whole qianwen window)
window_crop = img.crop((0, 0, 2880, 1704))
window_crop.save('C:/Users/15041/.openclaw/workspace/qianwen_chat_full.png')

# Save just the message area (top 2/3)
msg_crop = img.crop((0, 0, 2880, 1136))
msg_crop.save('C:/Users/15041/.openclaw/workspace/qianwen_chat_msg.png')

print(f"Saved screenshots")
print(f"Full: {window_crop.size}")
print(f"Msg: {msg_crop.size}")
print("Files:")
for f in ['qianwen_chat_full.png', 'qianwen_chat_msg.png']:
    path = f'C:/Users/15041/.openclaw/workspace/{f}'
    size = os.path.getsize(path)
    print(f"  {f}: {size} bytes")
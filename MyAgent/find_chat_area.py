"""
尝试用不同的方式获取聊天内容
"""
import pyautogui
import time
import win32gui
import pyperclip

hwnd = 1575860
win32gui.SetForegroundWindow(hwnd)
time.sleep(0.5)

# Try different click locations to find the chat message area
# The window client area is (13, 56, 2867, 1692) on screen
# Messages likely appear in the upper-middle area
# Let's try clicking at different Y positions to find where messages are

positions = [
    (1434, 300),  # upper area
    (1434, 500),  # middle-upper
    (1434, 700),  # middle
    (1434, 900),  # middle-lower
]

for x, y in positions:
    pyautogui.click(x=x, y=y)
    time.sleep(0.2)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.2)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.3)
    clip = pyperclip.paste()
    print(f"Clicked ({x},{y}): {len(clip)} chars - {repr(clip[:100])}")
    if len(clip) > 200 and 'Qwen1433' not in clip and 'API' not in clip:
        print("  ^^^ 可能获取到了聊天内容!")
        break
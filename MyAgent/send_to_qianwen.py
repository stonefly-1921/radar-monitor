import pyautogui
import time
import win32gui
import pyperclip

# Focus Qwen window
hwnd = 1575860
win32gui.SetForegroundWindow(hwnd)
time.sleep(0.3)

# Read the generated prompt
with open('C:/Users/15041/.openclaw/workspace/MyAgent/io/prompt.txt', 'r', encoding='utf-8') as f:
    prompt_text = f.read()

# Click on the input area of Qwen dialog
# Based on our analysis: input area is at bottom of window
pyautogui.click(x=1434, y=1500)
time.sleep(0.2)

# Copy prompt to clipboard and paste
pyperclip.copy(prompt_text)
time.sleep(0.1)
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.5)

print("Prompt pasted to Qwen dialog")
print(f"Clipboard has {len(prompt_text)} chars")

# Press Enter to send
pyautogui.press('enter')
print("Sent - now waiting for response...")
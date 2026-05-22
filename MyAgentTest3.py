import sys, time
import subprocess

sys.stdout.write('START\n')
sys.stdout.flush()

# Click on Qwen window using Windows Forms mouse_event
hwnd = 133298
import ctypes
user32 = ctypes.windll.user32

# First focus the window
user32.SetForegroundWindow(hwnd)
time.sleep(0.5)
sys.stdout.write('WINDOW_FOCUSED\n')
sys.stdout.flush()

# Click in the middle of the window to focus input
# Use mouse_event
MOUSEEVENTF_LEFTDOWN = 0x02
MOUSEEVENTF_LEFTUP = 0x04

# Get screen coords - Qwen window rect: L=-13, T=-13, R=2893, B=1717
L, T, R, B = -13, -13, 2893, 1717
click_x = L + (R - L) // 2
click_y = T + int((B - T) * 0.7)

# Move mouse and click
user32.SetCursorPos(click_x, click_y)
time.sleep(0.2)
user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
time.sleep(0.05)
user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
sys.stdout.write('CLICKED:' + str(click_x) + ',' + str(click_y) + '\n')
sys.stdout.flush()

time.sleep(0.3)

# Send short test text via SendKeys (no clipboard needed)
text = "Hello from MyAgent!"
subprocess.run([
    'powershell', '-ExecutionPolicy', 'Bypass', '-File',
    'C:/Users/15041/.openclaw/workspace/keyboard_control.ps1.txt', '-Text', text
], timeout=10)
sys.stdout.write('KEYS_SENT\n')
sys.stdout.flush()

# Press Enter
subprocess.run([
    'powershell', '-ExecutionPolicy', 'Bypass', '-Command',
    'Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")'
], timeout=5)
sys.stdout.write('ENTER_SENT\n')
sys.stdout.flush()

# Wait for response
time.sleep(5)

# Take screenshot
from PIL import ImageGrab
img = ImageGrab.grab(bbox=(L, T, R, B))
img.save('C:/Users/15041/.openclaw/workspace/qwen_result.png')
sys.stdout.write('SCREENSHOT_SAVED:' + str(img.size) + '\n')
sys.stdout.flush()
sys.stdout.write('ALL_DONE\n')
sys.stdout.flush()
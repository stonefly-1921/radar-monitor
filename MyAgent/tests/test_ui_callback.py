# -*- coding: utf-8 -*-
"""UI callback test - verify button callbacks actually fire."""
import pyautogui, pyperclip, time, os, sys

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.4

WORKSPACE = "C:\\Users\\15041\\.openclaw\\workspace\\MyAgent"
WIN_LEFT, WIN_TOP, WIN_W, WIN_H = 208, 208, 1832, 1278
WIN_CENTER_X = WIN_LEFT + WIN_W // 2

def click_at(x, y, label=""):
    print(f"  Click {label} at ({x}, {y})")
    pyautogui.click(x, y)
    time.sleep(0.5)

def type_text(text):
    pyperclip.copy(text)
    time.sleep(0.2)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.3)

def get_text(x, y, w, h):
    cx, cy = x + w // 2, y + h // 2
    pyautogui.click(cx, cy)
    time.sleep(0.4)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.3)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.3)
    return pyperclip.paste()

def save_shot(name):
    region = (WIN_LEFT, WIN_TOP, WIN_W, WIN_H)
    return pyautogui.screenshot(os.path.join(WORKSPACE, name), region=region)

print("=" * 60)
print("MyAgent UI Callback Test")
print("=" * 60)

# Activate
wins = pyautogui.getWindowsWithTitle('MyAgent')
if not wins:
    print("ERROR: No MyAgent window")
    exit(1)
win = wins[0]
win.restore()
win.activate()
time.sleep(0.5)

# Verify window still at same position
WIN_LEFT, WIN_TOP = win.left, win.top
WIN_W, WIN_H = win.width, win.height
WIN_CENTER_X = WIN_LEFT + WIN_W // 2
LEFT_W = WIN_CENTER_X - WIN_LEFT

print(f"\nWindow: ({WIN_LEFT},{WIN_TOP},{WIN_W},{WIN_H})")

# Try clicking and verify status bar changes
# Status bar should be at WIN_TOP + WIN_H - 30
STATUS_Y = WIN_TOP + WIN_H - 30
STATUS_X = WIN_LEFT + 10

# First read status bar
print("\n[1] Reading status bar...")
status1 = get_text(STATUS_X, STATUS_Y - 25, WIN_W - 20, 25)
print(f"  Status: '{status1.strip()}'")

# Click task input and type something
print("\n[2] Entering task...")
TASK_X = WIN_LEFT + 30
TASK_Y = WIN_TOP + 80  # Just below title bar
TASK_W = LEFT_W - 60
TASK_H = 120

click_at(TASK_X + 10, TASK_Y + 10, "task input")
type_text("测试任务")
save_shot('callback_1_task.png')

# Check text in input
text1 = get_text(TASK_X, TASK_Y, TASK_W, TASK_H)
print(f"  Task input: '{text1.strip()}'")

# Click 开始任务 (estimate: below task input)
START_Y = TASK_Y + TASK_H + 20
print(f"\n[3] Clicking 开始任务 at ({WIN_LEFT + 40 + 80}, {START_Y + 18})...")
pyautogui.click(WIN_LEFT + 40 + 80, START_Y + 18)
time.sleep(1.0)
save_shot('callback_2_after_start.png')

# Read status bar again - did it change?
status2 = get_text(STATUS_X, STATUS_Y - 25, WIN_W - 20, 25)
print(f"  Status after start: '{status2.strip()}'")

# Check task input text
text2 = get_text(TASK_X, TASK_Y, TASK_W, TASK_H)
print(f"  Task input after start: '{text2.strip()}'")

# Look at prompt area (right panel)
RIGHT_X = WIN_CENTER_X
RIGHT_W = WIN_W - LEFT_W
PROMPT_X = RIGHT_X + 30
PROMPT_Y = WIN_TOP + 80
PROMPT_W = RIGHT_W - 60
PROMPT_H = 250

print(f"\n[4] Checking prompt area...")
prompt = get_text(PROMPT_X, PROMPT_Y, PROMPT_W, PROMPT_H)
print(f"  Prompt ({len(prompt)} chars): '{prompt.strip()[:100]}'")

# Check response area
RESP_Y = PROMPT_Y + PROMPT_H + 20
RESP_H = 300
RESP_W = RIGHT_W - 60

print(f"\n[5] Checking response area...")
resp = get_text(PROMPT_X, RESP_Y, RESP_W, RESP_H)
print(f"  Response ({len(resp)} chars): '{resp.strip()[:100]}'")

# Check log area
LOG_X = WIN_LEFT + 30
LOG_Y = START_Y + 40
LOG_H = 320
LOG_W = LEFT_W - 60

print(f"\n[6] Checking log area...")
log = get_text(LOG_X, LOG_Y, LOG_W, LOG_H)
print(f"  Log ({len(log)} chars): '{log.strip()[:200]}'")

# Save final screenshot
save_shot('callback_final.png')

print("\n" + "=" * 60)
print("Test complete!")
print(f"Status changed: {status1.strip() != status2.strip()}")
print("Screenshots:", WORKSPACE + "/callback_*.png")
print("=" * 60)
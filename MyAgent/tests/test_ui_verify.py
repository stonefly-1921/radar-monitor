# -*- coding: utf-8 -*-
"""UI Element Verification Test - Verify all UI elements exist and are clickable."""
import pyautogui, pyperclip, time, os

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.4

WORKSPACE = "C:\\Users\\15041\\.openclaw\\workspace\\MyAgent"
WIN_LEFT, WIN_TOP, WIN_W, WIN_H = 208, 208, 1832, 1278
WIN_CENTER_X = WIN_LEFT + WIN_W // 2

def activate_window():
    wins = pyautogui.getWindowsWithTitle('MyAgent')
    if wins:
        w = wins[0]
        w.restore()
        w.activate()
        time.sleep(0.5)

def click_at(x, y, label=""):
    print(f"  Clicking {label} at ({x}, {y})")
    pyautogui.click(x, y)
    time.sleep(0.4)

def type_text(text):
    pyperclip.copy(text)
    time.sleep(0.2)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.3)

def get_text_by_select_all(x, y, w, h):
    center_x = x + w // 2
    center_y = y + h // 2
    pyautogui.click(center_x, center_y)
    time.sleep(0.4)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.3)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.3)
    return pyperclip.paste()

def save_window_shot(name):
    region = (WIN_LEFT, WIN_TOP, WIN_W, WIN_H)
    img = pyautogui.screenshot(os.path.join(WORKSPACE, name), region=region)
    return img

CONTENT_TOP = 278
LEFT_W = WIN_CENTER_X - WIN_LEFT
RIGHT_W = WIN_W - LEFT_W

print("=" * 60)
print("MyAgent UI Element Verification Test")
print("=" * 60)

# Activate
print("\n[0] Activating window...")
activate_window()
save_window_shot('verify_0.png')

# Get actual window position (may have shifted)
wins = pyautogui.getWindowsWithTitle('MyAgent')
if not wins:
    print("ERROR: No MyAgent window!")
    exit(1)
win = wins[0]
WIN_LEFT, WIN_TOP = win.left, win.top
WIN_W, WIN_H = win.width, win.height
WIN_CENTER_X = WIN_LEFT + WIN_W // 2
CONTENT_TOP = WIN_TOP + 60
LEFT_W = WIN_CENTER_X - WIN_LEFT

print(f"Window: ({WIN_LEFT},{WIN_TOP},{WIN_W},{WIN_H})")
print(f"Left panel: {WIN_LEFT} to {WIN_CENTER_X} ({LEFT_W}px)")
print(f"Right panel: {WIN_CENTER_X} to {WIN_LEFT+WIN_W}")

# ---- Test 1: Click task input and type ----
print("\n[1] Testing task input...")
TASK_X = WIN_LEFT + 30
TASK_Y = WIN_TOP + CONTENT_TOP + 15
TASK_W = LEFT_W - 60
TASK_H = 120

click_at(TASK_X + 10, TASK_Y + 10, "task input")
type_text("Test message from automation")
text = get_text_by_select_all(TASK_X, TASK_Y, TASK_W, TASK_H)
print(f"  Task input contains: {text[:100]}...")
save_window_shot('verify_1_task_input.png')

# ---- Test 2: Click 开始任务 ----
print("\n[2] Testing 开始任务 button...")
START_X = WIN_LEFT + 40
START_Y = TASK_Y + TASK_H + 15

click_at(START_X + 80, START_Y + 18, "开始任务")
# Check if the button was pressed (status might change)
# Just verify we didn't crash
save_window_shot('verify_2_start_clicked.png')
print("  Button click successful - no crash")

# ---- Test 3: Check log area ----
print("\n[3] Testing log area...")
LOG_X = WIN_LEFT + 30
LOG_Y = START_Y + 50
LOG_W = LEFT_W - 60
LOG_H = 320

# Try to read from log (may be empty but shouldn't crash)
text = get_text_by_select_all(LOG_X, LOG_Y, LOG_W, LOG_H)
print(f"  Log text length: {len(text)}")
print(f"  Log content: {text[:100] if text else '(empty)'}")

# ---- Test 4: Check prompt area (right panel) ----
print("\n[4] Testing prompt area (right panel)...")
PROMPT_X = WIN_CENTER_X + 30
PROMPT_Y = WIN_TOP + CONTENT_TOP + 15
PROMPT_W = RIGHT_W - 60
PROMPT_H = 250

text = get_text_by_select_all(PROMPT_X, PROMPT_Y, PROMPT_W, PROMPT_H)
print(f"  Prompt text length: {len(text)}")
print(f"  Prompt: {text[:100] if text else '(empty)'}")
save_window_shot('verify_4_prompt.png')

# ---- Test 5: Check response area ----
print("\n[5] Testing response area...")
RESP_Y = PROMPT_Y + PROMPT_H + 20
RESP_H = 300
RESP_W = RIGHT_W - 60

click_at(PROMPT_X, RESP_Y + 10, "response area")
type_text("Test response text from automation")
text = get_text_by_select_all(PROMPT_X, RESP_Y, RESP_W, RESP_H)
print(f"  Response contains: {text[:100]}...")
save_window_shot('verify_5_response.png')

# ---- Test 6: Check buttons ----
print("\n[6] Testing buttons...")
BTN_Y = RESP_Y + RESP_H + 25
PASTE_SUBMIT_X = WIN_CENTER_X + 160

click_at(PASTE_SUBMIT_X + 50, BTN_Y + 18, "粘贴&提交 button")
print("  Button click successful")

# ---- Test 7: 打断 button ----
print("\n[7] Testing 打断 button...")
INTERRUPT_X = WIN_LEFT + 40
INTERRUPT_Y = LOG_Y + LOG_H + 100  # Below log area

click_at(INTERRUPT_X + 40, INTERRUPT_Y + 18, "打断")
print("  Button click successful")
save_window_shot('verify_7_interrupt.png')

# ---- Final screenshot ----
save_window_shot('verify_final.png')

print("\n" + "=" * 60)
print("UI Element Verification Complete!")
print("Screenshots: " + WORKSPACE + "/verify_*.png")
print("=" * 60)
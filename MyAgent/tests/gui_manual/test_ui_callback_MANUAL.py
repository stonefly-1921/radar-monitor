# NOTE: This is a MANUAL pyautogui GUI test, not a unit test.
# Run manually: python -m pyautogui runtests
# @pytest.mark.skip
     1|# -*- coding: utf-8 -*-
     2|"""UI callback test - verify button callbacks actually fire."""
     3|import pyautogui, pyperclip, time, os, sys
     4|
     5|pyautogui.FAILSAFE = True
     6|pyautogui.PAUSE = 0.4
     7|
     8|WORKSPACE = "C:\\Users\\15041\\.openclaw\\workspace\\MyAgent"
     9|WIN_LEFT, WIN_TOP, WIN_W, WIN_H = 208, 208, 1832, 1278
    10|WIN_CENTER_X = WIN_LEFT + WIN_W // 2
    11|
    12|def click_at(x, y, label=""):
    13|    print(f"  Click {label} at ({x}, {y})")
    14|    pyautogui.click(x, y)
    15|    time.sleep(0.5)
    16|
    17|def type_text(text):
    18|    pyperclip.copy(text)
    19|    time.sleep(0.2)
    20|    pyautogui.hotkey('ctrl', 'v')
    21|    time.sleep(0.3)
    22|
    23|def get_text(x, y, w, h):
    24|    cx, cy = x + w // 2, y + h // 2
    25|    pyautogui.click(cx, cy)
    26|    time.sleep(0.4)
    27|    pyautogui.hotkey('ctrl', 'a')
    28|    time.sleep(0.3)
    29|    pyautogui.hotkey('ctrl', 'c')
    30|    time.sleep(0.3)
    31|    return pyperclip.paste()
    32|
    33|def save_shot(name):
    34|    region = (WIN_LEFT, WIN_TOP, WIN_W, WIN_H)
    35|    return pyautogui.screenshot(os.path.join(WORKSPACE, name), region=region)
    36|
    37|print("=" * 60)
    38|print("MyAgent UI Callback Test")
    39|print("=" * 60)
    40|
    41|# Activate
    42|wins = pyautogui.getWindowsWithTitle('MyAgent')
    43|if not wins:
    44|    print("ERROR: No MyAgent window")
    45|    exit(1)
    46|win = wins[0]
    47|win.restore()
    48|win.activate()
    49|time.sleep(0.5)
    50|
    51|# Verify window still at same position
    52|WIN_LEFT, WIN_TOP = win.left, win.top
    53|WIN_W, WIN_H = win.width, win.height
    54|WIN_CENTER_X = WIN_LEFT + WIN_W // 2
    55|LEFT_W = WIN_CENTER_X - WIN_LEFT
    56|
    57|print(f"\nWindow: ({WIN_LEFT},{WIN_TOP},{WIN_W},{WIN_H})")
    58|
    59|# Try clicking and verify status bar changes
    60|# Status bar should be at WIN_TOP + WIN_H - 30
    61|STATUS_Y = WIN_TOP + WIN_H - 30
    62|STATUS_X = WIN_LEFT + 10
    63|
    64|# First read status bar
    65|print("\n[1] Reading status bar...")
    66|status1 = get_text(STATUS_X, STATUS_Y - 25, WIN_W - 20, 25)
    67|print(f"  Status: '{status1.strip()}'")
    68|
    69|# Click task input and type something
    70|print("\n[2] Entering task...")
    71|TASK_X = WIN_LEFT + 30
    72|TASK_Y = WIN_TOP + 80  # Just below title bar
    73|TASK_W = LEFT_W - 60
    74|TASK_H = 120
    75|
    76|click_at(TASK_X + 10, TASK_Y + 10, "task input")
    77|type_text("测试任务")
    78|save_shot('callback_1_task.png')
    79|
    80|# Check text in input
    81|text1 = get_text(TASK_X, TASK_Y, TASK_W, TASK_H)
    82|print(f"  Task input: '{text1.strip()}'")
    83|
    84|# Click 开始任务 (estimate: below task input)
    85|START_Y = TASK_Y + TASK_H + 20
    86|print(f"\n[3] Clicking 开始任务 at ({WIN_LEFT + 40 + 80}, {START_Y + 18})...")
    87|pyautogui.click(WIN_LEFT + 40 + 80, START_Y + 18)
    88|time.sleep(1.0)
    89|save_shot('callback_2_after_start.png')
    90|
    91|# Read status bar again - did it change?
    92|status2 = get_text(STATUS_X, STATUS_Y - 25, WIN_W - 20, 25)
    93|print(f"  Status after start: '{status2.strip()}'")
    94|
    95|# Check task input text
    96|text2 = get_text(TASK_X, TASK_Y, TASK_W, TASK_H)
    97|print(f"  Task input after start: '{text2.strip()}'")
    98|
    99|# Look at prompt area (right panel)
   100|RIGHT_X = WIN_CENTER_X
   101|RIGHT_W = WIN_W - LEFT_W
   102|PROMPT_X = RIGHT_X + 30
   103|PROMPT_Y = WIN_TOP + 80
   104|PROMPT_W = RIGHT_W - 60
   105|PROMPT_H = 250
   106|
   107|print(f"\n[4] Checking prompt area...")
   108|prompt = get_text(PROMPT_X, PROMPT_Y, PROMPT_W, PROMPT_H)
   109|print(f"  Prompt ({len(prompt)} chars): '{prompt.strip()[:100]}'")
   110|
   111|# Check response area
   112|RESP_Y = PROMPT_Y + PROMPT_H + 20
   113|RESP_H = 300
   114|RESP_W = RIGHT_W - 60
   115|
   116|print(f"\n[5] Checking response area...")
   117|resp = get_text(PROMPT_X, RESP_Y, RESP_W, RESP_H)
   118|print(f"  Response ({len(resp)} chars): '{resp.strip()[:100]}'")
   119|
   120|# Check log area
   121|LOG_X = WIN_LEFT + 30
   122|LOG_Y = START_Y + 40
   123|LOG_H = 320
   124|LOG_W = LEFT_W - 60
   125|
   126|print(f"\n[6] Checking log area...")
   127|log = get_text(LOG_X, LOG_Y, LOG_W, LOG_H)
   128|print(f"  Log ({len(log)} chars): '{log.strip()[:200]}'")
   129|
   130|# Save final screenshot
   131|save_shot('callback_final.png')
   132|
   133|print("\n" + "=" * 60)
   134|print("Test complete!")
   135|print(f"Status changed: {status1.strip() != status2.strip()}")
   136|print("Screenshots:", WORKSPACE + "/callback_*.png")
   137|print("=" * 60)
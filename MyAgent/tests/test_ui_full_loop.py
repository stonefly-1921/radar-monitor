# -*- coding: utf-8 -*-
"""Full GUI automation loop test with MiniMax API - FIXED content parsing."""
import json, urllib.request, os, sys, time
import pyautogui
import pyperclip

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5

WORKSPACE = "C:\\Users\\15041\\.openclaw\\workspace\\MyAgent"

# ============ MiniMax API ============

def call_minimax(prompt_text, model="MiniMax-M2.7", max_tokens=500):
    key = open(os.path.join(WORKSPACE, '_apikey.txt')).read().strip()
    url = 'https://api.minimaxi.com/anthropic/v1/messages'
    headers = {
        'Authorization': 'Bearer ' + key,
        'Content-Type': 'application/json',
        'anthropic-version': '2023-06-01'
    }
    payload = {
        'model': model,
        'messages': [{'role': 'user', 'content': prompt_text}],
        'max_tokens': max_tokens
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            if result.get('base_resp', {}).get('status_code') != 0:
                return None, result.get('base_resp', {}).get('status_msg', 'unknown error')

            # Parse content - may have both thinking and text entries
            content = result.get('content', [])
            text_parts = []
            for item in content:
                if item.get('type') == 'text':
                    text_parts.append(item.get('text', ''))
            text = ''.join(text_parts)
            return text, None
    except Exception as e:
        return None, str(e)

# ============ GUI helpers ============

WIN_LEFT, WIN_TOP, WIN_W, WIN_H = 208, 208, 1832, 1278
WIN_CENTER_X = WIN_LEFT + WIN_W // 2
WIN_CENTER_Y = WIN_TOP + WIN_H // 2
CONTENT_TOP = 278

LEFT_W = WIN_CENTER_X - WIN_LEFT

TASK_INPUT_X = WIN_LEFT + 30
TASK_INPUT_Y = WIN_TOP + CONTENT_TOP + 15
TASK_INPUT_W = LEFT_W - 60
TASK_INPUT_H = 120

START_BTN_X = WIN_LEFT + 40
START_BTN_Y = TASK_INPUT_Y + TASK_INPUT_H + 15

LOG_X = WIN_LEFT + 30
LOG_Y = START_BTN_Y + 50
LOG_H = 320
LOG_W = LEFT_W - 60

FINAL_Y = LOG_Y + LOG_H + 20
FINAL_H = 150

RIGHT_X = WIN_CENTER_X
RIGHT_W = WIN_W - LEFT_W

PROMPT_X = RIGHT_X + 30
PROMPT_Y = WIN_TOP + CONTENT_TOP + 15
PROMPT_W = RIGHT_W - 60
PROMPT_H = 250

RESP_X = RIGHT_X + 30
RESP_Y = PROMPT_Y + PROMPT_H + 20
RESP_W = RIGHT_W - 60
RESP_H = 300

BTN_Y = RESP_Y + RESP_H + 25
PASTE_SUBMIT_BTN_X = RIGHT_X + 160


def activate_window():
    wins = pyautogui.getWindowsWithTitle('MyAgent')
    if wins:
        w = wins[0]
        w.restore()
        w.activate()
        time.sleep(0.5)


def click_at(x, y):
    pyautogui.click(x, y)
    time.sleep(0.3)


def type_text_ctrl_v(text):
    pyperclip.copy(text)
    time.sleep(0.2)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.3)


def get_text_ctrl_ac(x, y, w, h):
    center_x = x + w // 2
    center_y = y + h // 2
    pyautogui.click(center_x, center_y)
    time.sleep(0.4)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.3)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.3)
    return pyperclip.paste()


def save_screenshot(name):
    region = (WIN_LEFT, WIN_TOP, WIN_W, WIN_H)
    img = pyautogui.screenshot(os.path.join(WORKSPACE, name), region=region)


def run_full_loop():
    print("=" * 60)
    print("MyAgent GUI Full Loop Test")
    print("=" * 60)

    # Step 0: Activate
    print("\n[0] Activating MyAgent window...")
    activate_window()
    save_screenshot('gui_0_active.png')

    # Step 1: Enter task
    print("\n[1] Entering task...")
    click_at(TASK_INPUT_X + 10, TASK_INPUT_Y + 10)
    type_text_ctrl_v("你好，简单介绍一下自己")
    save_screenshot('gui_1_task.png')

    # Step 2: Click 开始任务
    print("\n[2] Clicking 开始任务...")
    click_at(START_BTN_X + 80, START_BTN_Y + 18)
    time.sleep(1.5)
    save_screenshot('gui_2_after_start.png')

    # Step 3: Wait for prompt
    print("\n[3] Waiting for prompt...")
    prompt_text = None
    for i in range(10):
        time.sleep(1.5)
        save_screenshot(f'gui_3_wait_{i}.png')
        text = get_text_ctrl_ac(PROMPT_X, PROMPT_Y, PROMPT_W, PROMPT_H)
        print(f"  Attempt {i+1}: {len(text)} chars")
        if text and len(text.strip()) > 30:
            prompt_text = text.strip()
            print(f"  Found prompt! ({len(prompt_text)} chars)")
            break

    save_screenshot('gui_3_done.png')

    if not prompt_text or len(prompt_text) < 30:
        print("  Using fallback prompt")
        prompt_text = "请用中文简单介绍自己，只用一句话"
        print(f"  Fallback: {prompt_text}")

    # Step 4: Call MiniMax
    print("\n[4] Calling MiniMax API...")
    print(f"  Prompt: {prompt_text[:80]}...")
    resp_text, error = call_minimax(prompt_text)
    if error:
        print(f"  API Error: {error}")
        return False
    print(f"  Response ({len(resp_text)} chars): {resp_text[:200]}...")

    # Step 5: Paste response
    print("\n[5] Pasting response...")
    click_at(RESP_X + 10, RESP_Y + 10)
    type_text_ctrl_v(resp_text)
    save_screenshot('gui_5_pasted.png')

    # Step 6: Click 粘贴&提交
    print("\n[6] Clicking 粘贴&提交...")
    click_at(PASTE_SUBMIT_BTN_X + 50, BTN_Y + 18)
    time.sleep(2.0)
    save_screenshot('gui_6_submitted.png')

    # Step 7: Read result
    print("\n[7] Reading result...")
    log_text = get_text_ctrl_ac(LOG_X, LOG_Y, LOG_W, LOG_H)
    print(f"  Log: {log_text[:300] if log_text else '(empty)'}")
    save_screenshot('gui_7_final.png')

    print("\n" + "=" * 60)
    print("Test completed!")
    print(f"  Prompt: {prompt_text[:80]}...")
    print(f"  API response: {resp_text[:100]}...")
    print(f"  Log chars: {len(log_text)}")
    print(f"  Screenshots: {WORKSPACE}/gui_*.png")
    print("=" * 60)
    return True


if __name__ == '__main__':
    try:
        success = run_full_loop()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
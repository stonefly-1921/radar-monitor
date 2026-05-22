import sys, time, ctypes
import subprocess

user32 = ctypes.windll.user32
SetForegroundWindow = user32.SetForegroundWindow
SetCursorPos = user32.SetCursorPos
mouse_event = user32.mouse_event
IsIconic = user32.IsIconic
ShowWindow = user32.ShowWindow
EnumWindows = user32.EnumWindows
GetWindowText = user32.GetWindowTextW
GetWindowRect = user32.GetWindowRect
L_click = 0x02
L_up = 0x04

sys.path.insert(0, 'C:/Users/15041/.openclaw/workspace/MyAgent')
from agent.loop_v2 import AgentLoopV2

def find_qwen():
    windows = []
    def callback(hwnd, lParam):
        if IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buf, length + 1)
                title = buf.value
                if '千问' in title:
                    class RECT(ctypes.Structure):
                        _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
                    r = RECT()
                    GetWindowRect(hwnd, ctypes.byref(r))
                    windows.append((hwnd, title, r.left, r.top, r.right, r.bottom))
        return True
    EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(callback), 0)
    return windows[0] if windows else None

def send_keys_to_qwen(win_info, text):
    """Use pywinauto to send text to Qwen's edit field"""
    from pywinauto import Application
    from pywinauto.keyboard import send_keys
    
    hwnd, title, L, T, R, B = win_info
    
    if IsIconic(hwnd):
        ShowWindow(hwnd, 9)
        time.sleep(1.0)
        class RECT(ctypes.Structure):
            _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
        r = RECT()
        GetWindowRect(hwnd, ctypes.byref(r))
        L, T, R, B = r.left, r.top, r.right, r.bottom
    
    # Use pywinauto to click and type
    app = Application(backend='uia')
    app.connect(process=21024)
    win = app.window(title='千问')
    win.set_focus()
    time.sleep(0.5)
    
    # Click in the input area (bottom part of window)
    w, h = R - L, B - T
    cx = L + w // 2
    cy = T + int(h * 0.88)
    mouse.click(coords=(cx, cy))
    time.sleep(0.5)
    
    # Type text directly (short text)
    send_keys(text)
    time.sleep(0.3)
    send_keys('{ENTER}')

print('[1] Initialize MyAgent...')
loop = AgentLoopV2()
loop.base_dir = 'C:/Users/15041/.openclaw/workspace/MyAgent'
loop.initialize()

task = '用Python写一个快速排序算法'
with open('C:/Users/15041/.openclaw/workspace/MyAgent/io/input.txt', 'w', encoding='utf-8') as f:
    f.write(task)
print('[2] Task: ' + task)

loop.session.add_turn({'input': task})
conversation = loop.session.get_conversation_history()
prompt_text = loop.build_prompt_text(task, 1, None, conversation)
loop._save_prompt(prompt_text)
print('[3] prompt.txt saved (' + str(len(prompt_text)) + ' chars)')

print('[4] Finding Qwen...')
qwen = find_qwen()
if not qwen:
    print('ERROR: Qwen not found!')
    sys.exit(1)
print('[5] Qwen: ' + qwen[1])

# Send short test first to verify click lands in input
print('[6] Sending short test to Qwen...')
send_keys_to_qwen(qwen, 'Hi Qwen, this is a test.')
print('[7] Test sent')

time.sleep(5)

# Screenshot
hwnd, title, L, T, R, B = qwen
if IsIconic(hwnd):
    ShowWindow(hwnd, 9)
    time.sleep(1.0)
    class RECT(ctypes.Structure):
        _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
    r = RECT()
    GetWindowRect(hwnd, ctypes.byref(r))
    L, T, R, B = r.left, r.top, r.right, r.bottom

from PIL import ImageGrab
img = ImageGrab.grab(bbox=(L, T, R, B))
img.save('C:/Users/15041/.openclaw/workspace/qwen_final.png')
print('[8] Screenshot saved')
print('[9] DONE')
import sys, time, ctypes
from PIL import ImageGrab
import subprocess
from pywinauto import Application
from pywinauto.keyboard import send_keys

user32 = ctypes.windll.user32

# Define at global level for ctypes callback access
IsWindowVisible = user32.IsWindowVisible
IsIconic = user32.IsIconic
ShowWindow = user32.ShowWindow
SetForegroundWindow = user32.SetForegroundWindow
SetCursorPos = user32.SetCursorPos
mouse_event = user32.mouse_event
EnumWindows = user32.EnumWindows
GetWindowText = user32.GetWindowTextW
GetWindowRect = user32.GetWindowRect
L_click = 0x02
L_up = 0x04

sys.path.insert(0, 'C:/Users/15041/.openclaw/workspace/MyAgent')
from agent.loop_v2 import AgentLoopV2

# Global storage for window find result
_found_window = None

def _enum_callback(hwnd, lParam):
    global _found_window
    if IsWindowVisible(hwnd):
        length = GetWindowText(hwnd, ctypes.create_unicode_buffer(1), 0)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            GetWindowText(hwnd, buf, length + 1)
            title = buf.value
            if '千问' in title:
                class RECT(ctypes.Structure):
                    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
                r = RECT()
                GetWindowRect(hwnd, ctypes.byref(r))
                _found_window = (hwnd, title, r.left, r.top, r.right, r.bottom)
                return False  # Stop enumeration
    return True

def find_qwen():
    global _found_window
    _found_window = None
    EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(_enum_callback), 0)
    return _found_window

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

hwnd, title, L, T, R, B = qwen

if IsIconic(hwnd):
    ShowWindow(hwnd, 9)
    time.sleep(1.0)
    class RECT(ctypes.Structure):
        _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
    r = RECT()
    GetWindowRect(hwnd, ctypes.byref(r))
    L, T, R, B = r.left, r.top, r.right, r.bottom

SetForegroundWindow(hwnd)
time.sleep(0.5)

# Click via pywinauto - use the app to click on the edit element
app = Application(backend='uia')
app.connect(process=21024)
win = app.window(title='千问')
win.set_focus()
time.sleep(0.3)

# Try to find and click the input field
try:
    edit = win.child_window(control_type='Edit')
    edit.set_focus()
    time.sleep(0.2)
    print('[6] Found and focused Edit element')
except Exception as e:
    print('[6] Could not find Edit: ' + str(e))
    # Fallback: click at bottom-center of window
    w, h = R - L, B - T
    cx = L + w // 2
    cy = T + int(h * 0.9)
    SetCursorPos(cx, cy)
    time.sleep(0.2)
    mouse_event(L_click, 0, 0, 0, 0)
    time.sleep(0.05)
    mouse_event(L_up, 0, 0, 0, 0)
    print('[6] Clicked at (' + str(cx) + ',' + str(cy) + ')')
    time.sleep(0.5)

# Send short test text via send_keys (no clipboard needed for short text)
print('[7] Sending short test text via send_keys...')
send_keys('Hello Qwen from MyAgent!')
time.sleep(0.3)
send_keys('{ENTER}')
print('[8] Sent!')

# Wait for response
print('[9] Waiting 6s...')
time.sleep(6)

# Screenshot
img = ImageGrab.grab(bbox=(L, T, R, B))
img.save('C:/Users/15041/.openclaw/workspace/qwen_final.png')
print('[10] Screenshot saved')
print('[11] DONE')
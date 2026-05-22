import sys, time
from pywinauto import Application, mouse
from pywinauto.keyboard import send_keys
import subprocess

def ps_set_clipboard(text):
    p = subprocess.run(
        ['powershell', '-ExecutionPolicy', 'Bypass', '-File',
         'C:/Users/15041/.openclaw/workspace/setclip.ps1', '-Value', text],
        capture_output=True, timeout=10
    )
    return p.returncode == 0

# Step 1: Generate prompt.txt
sys.path.insert(0, 'C:/Users/15041/.openclaw/workspace/MyAgent')
from agent.loop_v2 import AgentLoopV2

loop = AgentLoopV2()
loop.base_dir = 'C:/Users/15041/.openclaw/workspace/MyAgent'
loop.initialize()

task = "用Python写一个快速排序算法"
with open('C:/Users/15041/.openclaw/workspace/MyAgent/io/input.txt', 'w', encoding='utf-8') as f:
    f.write(task)
sys.stdout.write('Task: ' + task + '\n')
sys.stdout.flush()

loop.session.add_turn({'input': task})
conversation = loop.session.get_conversation_history()
prompt_text = loop.build_prompt_text(task, 1, None, conversation)
loop._save_prompt(prompt_text)
sys.stdout.write('PROMPT_SAVED:' + str(len(prompt_text)) + '\n')
sys.stdout.flush()

# Step 2: Connect to Qwen
sys.stdout.write('Connecting to Qwen...\n')
sys.stdout.flush()
app = Application(backend='uia')
app.connect(process=21024)
win = app.window(title='千问')
win.set_focus()
time.sleep(0.3)

win_rect = win.element_info.rectangle
L, T, R, B = win_rect.left, win_rect.top, win_rect.right, win_rect.bottom

input_y = T + int((B - T) * 0.7)
mouse.click(coords=(L + (R-L)//2, input_y))
time.sleep(0.3)
sys.stdout.write('CLICKED_INPUT\n')
sys.stdout.flush()

# Step 3: Send via clipboard
ok = ps_set_clipboard(prompt_text[:1000])
sys.stdout.write('CLIPBOARD:' + str(ok) + '\n')
sys.stdout.flush()

send_keys('^v')
time.sleep(0.5)
send_keys('{ENTER}')
sys.stdout.write('SENT\n')
sys.stdout.flush()

# Step 4: Wait and screenshot
time.sleep(10)
sys.stdout.write('WAITING_DONE\n')
sys.stdout.flush()

from PIL import ImageGrab
img = ImageGrab.grab(bbox=(L, T, R, B))
img.save('C:/Users/15041/.openclaw/workspace/qwen_result.png')
sys.stdout.write('SCREENSHOT_SAVED:' + str(img.size) + '\n')
sys.stdout.flush()
sys.stdout.write('DONE\n')
sys.stdout.flush()
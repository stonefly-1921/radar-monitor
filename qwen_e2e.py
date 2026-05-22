import sys, time
from pywinauto import Application, mouse
from pywinauto.keyboard import send_keys

sys.path.insert(0, 'C:/Users/15041/.openclaw/workspace/MyAgent')
from agent.loop_v2 import AgentLoopV2

loop = AgentLoopV2()
loop.base_dir = 'C:/Users/15041/.openclaw/workspace/MyAgent'
loop.initialize()

with open('C:/Users/15041/.openclaw/workspace/MyAgent/io/input.txt', 'r', encoding='utf-8') as f:
    task = f.read().strip()
sys.stdout.write('TASK:' + task + '\n')
sys.stdout.flush()

loop.session.add_turn({'input': task})
conversation = loop.session.get_conversation_history()
prompt_text = loop.build_prompt_text(task, 1, None, conversation)
loop._save_prompt(prompt_text)
sys.stdout.write('PROMPT_SAVED:' + str(len(prompt_text)) + '\n')
sys.stdout.flush()

app = Application(backend='uia')
app.connect(process=21024)
win = app.window(title='千问')
win.set_focus()
time.sleep(0.5)

win_rect = win.element_info.rectangle
L = win_rect.left
T = win_rect.top
R = win_rect.right
B = win_rect.bottom
mouse.click(coords=(L + 200, T + (B-T)//2))
time.sleep(0.3)

send_keys('Say: Hello from MyAgent!{ENTER}')
sys.stdout.write('KEYS_SENT\n')
sys.stdout.flush()

time.sleep(5)
sys.stdout.write('WAIT_DONE\n')
sys.stdout.flush()

from PIL import ImageGrab
img = ImageGrab.grab(bbox=(L, T, R, B))
img.save('C:/Users/15041/.openclaw/workspace/qwen_response.png')
sys.stdout.write('SCREENSHOT_DONE\n')
sys.stdout.flush()
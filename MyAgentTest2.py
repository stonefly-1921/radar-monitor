import sys, time
from pywinauto import Application, mouse
from pywinauto.keyboard import send_keys
import subprocess

sys.stdout.write('START\n')
sys.stdout.flush()

# Test clipboard via PS file
p = subprocess.run(
    ['powershell', '-ExecutionPolicy', 'Bypass', '-File',
     'C:/Users/15041/.openclaw/workspace/setclip.ps1', '-Value', 'hello qwen test'],
    capture_output=True, timeout=10
)
sys.stdout.write('CLIP:' + str(p.returncode) + '\n')
sys.stdout.flush()

# Connect to Qwen
sys.stdout.write('CONNECTING\n')
sys.stdout.flush()
app = Application(backend='uia')
app.connect(process=21024)
win = app.window(title='千问')
win.set_focus()
sys.stdout.write('FOCUSED\n')
sys.stdout.flush()

time.sleep(0.3)

win_rect = win.element_info.rectangle
L, T, R, B = win_rect.left, win_rect.top, win_rect.right, win_rect.bottom
sys.stdout.write(f'RECT:{L},{T},{R},{B}\n')
sys.stdout.flush()

input_y = T + int((B - T) * 0.7)
mouse.click(coords=(L + (R-L)//2, input_y))
sys.stdout.write('CLICKED\n')
sys.stdout.flush()

time.sleep(0.3)
send_keys('^v')
time.sleep(0.3)
send_keys('{ENTER}')
sys.stdout.write('SENT_KEYS\n')
sys.stdout.flush()

time.sleep(3)
from PIL import ImageGrab
img = ImageGrab.grab(bbox=(L, T, R, B))
img.save('C:/Users/15041/.openclaw/workspace/qwen_result.png')
sys.stdout.write('SCREENSHOT_DONE\n')
sys.stdout.flush()
sys.stdout.write('ALL_DONE\n')
sys.stdout.flush()
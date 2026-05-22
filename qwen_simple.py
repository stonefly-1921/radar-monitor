import time
from pywinauto.keyboard import send_keys

# Just test if we can send keys
send_keys('Say: Hello from MyAgent!{ENTER}')
print('KEYS_SENT')
time.sleep(5)
from PIL import ImageGrab
img = ImageGrab.grab()
img.save('C:/Users/15041/.openclaw/workspace/qwen_test.png')
print('SCREENSHOT_DONE')
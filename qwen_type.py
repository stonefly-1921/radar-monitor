from pywinauto import Application, mouse
from pywinauto.keyboard import send_keys
import time

app = Application(backend='uia')
app.connect(process=21024)
win = app.window(title='千问')

win.set_focus()
time.sleep(0.5)

win_rect = win.element_info.rectangle
L, T, R, B = win_rect.left, win_rect.top, win_rect.right, win_rect.bottom
W, H = R - L, B - T
print('Window rect: L=%d T=%d W=%d H=%d' % (L, T, W, H))

# Click in the middle-left area where the input box should be
input_x = L + 200
input_y = T + H // 2
print('Clicking input area at screen coords:', input_x, input_y)
mouse.click(coords=(input_x, input_y))
time.sleep(0.5)

# Type prompt
send_keys('write hello world in python')
time.sleep(0.3)

# Click send button (bottom right area)
send_x = L + W - 80
send_y = T + H - 80
print('Clicking send at:', send_x, send_y)
mouse.click(coords=(send_x, send_y))
print('Done!')
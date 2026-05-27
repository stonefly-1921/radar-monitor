from pywinauto import Application
import time, os

app = Application(backend='win32').connect(process=18012)
win = app.window(title='MyAgent v2.1')

# 任务输入框 HWND=13700270
# 开始任务按钮 HWND=265380

# 点击任务输入框
task_input = None
for c in win.children():
    if c.handle == 13700270:
        task_input = c
        break

print(f'点击任务输入框: {task_input}')
task_input.click_input()
time.sleep(0.5)

# 用 set_edit_text 设置内容
test_text = 'Test task from automation'
try:
    task_input.set_edit_text(test_text)
    print(f'set_edit_text 成功: {test_text}')
except Exception as e:
    print(f'set_edit_text 失败: {e}')
    import pywinauto.keyboard as kb
    kb.send_keys('^a')
    time.sleep(0.1)
    kb.send_keys(test_text)
    print('用 kb.send_keys 输入')

time.sleep(1)

# 点击开始任务按钮
start_btn = None
for c in win.children():
    if c.handle == 265380:
        start_btn = c
        break

print(f'点击开始任务按钮: {start_btn}')
start_btn.click_input()
print('已点击')

time.sleep(3)

# 检查 io/input.txt
f = r'C:\Users\15041\.openclaw\workspace\MyAgent\io\input.txt'
size = os.path.getsize(f)
print(f'io/input.txt 大小: {size} bytes')
if size > 0:
    content = open(f, encoding='utf-8').read()
    print(f'内容: {content[:100]}')
else:
    print('文件为空')

# 检查 io/prompt.txt
f2 = r'C:\Users\15041\.openclaw\workspace\MyAgent\io\prompt.txt'
size2 = os.path.getsize(f2)
print(f'io/prompt.txt 大小: {size2} bytes')
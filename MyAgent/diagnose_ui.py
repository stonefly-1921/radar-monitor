"""诊断 MyAgent Tkinter 窗口结构"""
from pywinauto import Application
import time

app = Application(backend='win32').connect(process=18012)
win = app.window(title='MyAgent v2.1')

print("=== MyAgent v2.1 窗口诊断 ===")
print(f"Window rect: {win.rectangle()}")

# 遍历所有子控件
print("\n所有子控件:")
index = 0
for c in win.children():
    try:
        r = c.rectangle()
        ctrl_type = c.class_name
        hwnd = c.handle
        # TkChild 是 Tkinter 的控件，没有 window_text()
        text = ""
        try:
            text = c.window_text()
        except:
            pass
        print(f"  [{index}] HWND={hwnd} [{ctrl_type}] L={r.left},T={r.top},R={r.right},B={r.bottom} text={repr(text[:30])}")
        index += 1
    except Exception as e:
        print(f"  [{index}] Error: {e}")
        index += 1

# 找关键按钮
print("\n按钮列表:")
btn_index = 0
for c in win.children():
    try:
        if c.class_name == 'Button':
            r = c.rectangle()
            hwnd = c.handle
            print(f"  Button#{btn_index} HWND={hwnd} L={r.left},T={r.top},R={r.right},B={r.bottom}")
            btn_index += 1
    except:
        pass

# 尝试点击任务输入框并输入
print("\n尝试操作任务输入框...")
task_input = None
for c in win.children():
    try:
        r = c.rectangle()
        # 任务输入框：L=80,T=172,R=858,B=282
        if abs(r.left - 80) < 5 and abs(r.top - 172) < 5:
            task_input = c
            print(f"  找到任务输入框 HWND={c.handle}")
            c.click_input()
            time.sleep(0.5)
            import pywinauto.keyboard as kb
            kb.send_keys("Hello MyAgent!")
            time.sleep(0.5)
            print(f"  已输入文本")
            break
    except Exception as e:
        print(f"  操作失败: {e}")

print("\n诊断完成")
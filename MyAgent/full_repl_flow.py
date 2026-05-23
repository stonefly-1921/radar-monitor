"""
完整的 REPL 流程测试 - 模拟人工复制粘贴 (极简版)
"""
import pyautogui
import time
import win32gui
import pyperclip

# ============================================================
# Step 1: 找千问窗口
# ============================================================
print("Step 1: 找千问窗口")

found_windows = []
def enum_cb(hwnd, results):
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        if '千问' in title:
            results.append((hwnd, title))

win32gui.EnumWindows(enum_cb, found_windows)
print(f"找到: {found_windows}")

if not found_windows:
    print("ERROR: 千问窗口未找到!")
    exit(1)

hwnd_qianwen = found_windows[0][0]
print(f"HWND={hwnd_qianwen}")

# ============================================================
# Step 2: 聚焦窗口，粘贴，发送
# ============================================================
print("\nStep 2: 粘贴到千问对话框")

win32gui.SetForegroundWindow(hwnd_qianwen)
time.sleep(0.5)

# 点击输入框
pyautogui.click(x=1434, y=1550)
time.sleep(0.3)
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.1)
pyautogui.press('delete')
time.sleep(0.2)

# 粘贴任务
test_task = "请帮我统计一下 MyAgent/tests 目录下有多少个 Python 文件，然后把文件列表列出来。"
pyperclip.copy(test_task)
time.sleep(0.1)
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.5)
print("已粘贴")

# 发送
pyautogui.press('enter')
print("已发送，等待 15 秒...")
time.sleep(15)
print("等待结束")

# ============================================================
# Step 3: 截图
# ============================================================
print("\nStep 3: 截图")
pyautogui.screenshot('C:/Users/15041/.openclaw/workspace/repl_test_response.png')
print("截图已保存")

# ============================================================
# Step 4: 获取回复
# ============================================================
print("\nStep 4: 获取剪贴板内容")
pyautogui.click(x=1434, y=800)
time.sleep(0.2)
pyautogui.hotkey('ctrl', 'end')
time.sleep(0.2)
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.3)
pyautogui.hotkey('ctrl', 'c')
time.sleep(0.3)
clip = pyperclip.paste()
print(f"剪贴板长度: {len(clip)}")
print(f"内容: {repr(clip[:500])}")
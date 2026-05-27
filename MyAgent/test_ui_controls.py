"""
MyAgent UI 控件测试 - 验证每个按钮的实际效果

目标：
1. 逐一测试每个按钮控件是否真的有效
2. 观察点击后 io/ 文件的变化
3. 确认 response 粘贴区的实际行为

测试步骤：
1. 清空所有 io/ 文件（模拟干净状态）
2. 测试"开始任务"按钮 - 写 input.txt + 通知 REPL
3. 测试"粘贴&提交"按钮 - 写 response.txt + 通知 REPL
4. 观察 io/ 目录文件变化
5. 读取 UI 的 prompt 文本区内容，验证是否更新
"""
import sys, os, time, subprocess
from pywinauto import Application
import pywinauto.keyboard as kb

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'
IO_DIR = os.path.join(MYAGENT_DIR, 'io')

# ============ 环境准备 ============

def clean_io():
    """清空 io/ 目录下的关键文件"""
    for f in ['input.txt', 'prompt.txt', 'response.txt', 'tool_result.json', 'final_answer.txt']:
        path = os.path.join(IO_DIR, f)
        if os.path.exists(path):
            open(path, 'w', encoding='utf-8').write('')
    print('[清空] io/ 目录已清空')

def show_io():
    """显示 io/ 文件状态"""
    print('[IO 状态]')
    for f in ['input.txt', 'prompt.txt', 'response.txt', 'tool_result.json', 'final_answer.txt']:
        path = os.path.join(IO_DIR, f)
        size = os.path.getsize(path) if os.path.exists(path) else 0
        content = ''
        if size > 0:
            content = open(path, encoding='utf-8').read().strip()[:50]
        print(f'  {f}: {size} bytes | {content}')


# ============ 连接 UI ============

def get_controls():
    """获取所有控件"""
    app = Application(backend='win32').connect(process=18012)
    win = app.window(title='MyAgent v2.1')
    
    controls = {}
    for c in win.children():
        try:
            r = c.rectangle()
            controls[c.handle] = {
                'rect': (r.left, r.top, r.right, r.bottom),
                'class': str(c.class_name),
                'obj': c
            }
        except:
            pass
    
    return win, controls


def describe_control(win, hwnd, label):
    """打印控件详细信息"""
    c = [x for x in win.children() if x.handle == hwnd][0]
    r = c.rectangle()
    print(f'  [{label}] HWND={hwnd} [{c.class_name}] L={r.left},T={r.top},R={r.right},B={r.bottom}')


# ============ 测试1：开始任务按钮 ============

def test_start_button():
    """
    测试"开始任务"按钮（HWND=265380）
    
    预期效果：
    - 写入 io/input.txt
    - 通知 REPL 子进程（通过 stdin newline）
    - REPL 生成 prompt.txt
    
    验证方法：清空 io/ → 点击按钮 → 等待 5s → 检查 input.txt 和 prompt.txt
    """
    print('\n' + '='*60)
    print('测试1：开始任务按钮')
    print('='*60)
    
    win, controls = get_controls()
    
    # 清空
    clean_io()
    show_io()
    
    # 输入任务到输入框
    task_input = [c for c in win.children() if c.handle == 13700270][0]
    task_input.click_input()
    time.sleep(0.3)
    kb.send_keys('^a')
    time.sleep(0.1)
    kb.send_keys('{DELETE}')
    
    task = '测试任务：计算 1+1'
    subprocess.run(['powershell', '-Command', f'Set-Clipboard -Value "{task}"'], capture_output=True)
    time.sleep(0.3)
    kb.send_keys('^v')
    time.sleep(0.5)
    print(f'[输入] 已输入: {task}')
    
    # 点击开始任务按钮
    start_btn = [c for c in win.children() if c.handle == 265380][0]
    print(f'[点击] 开始任务按钮 HWND={start_btn.handle}')
    start_btn.click_input()
    
    # 等待
    print('[等待] 5秒...')
    time.sleep(5)
    
    # 检查结果
    print('\n[结果]')
    show_io()
    
    # 读 prompt 文本区内容
    prompt_area = [c for c in win.children() if c.handle == 330868][0]
    prompt_text = prompt_area.window_text()
    print(f'\n[UI Prompt 文本区] 长度={len(prompt_text)} chars')
    print(f'内容预览: {prompt_text[:200]}')


# ============ 测试2：粘贴&提交按钮 ============

def test_submit_button():
    """
    测试"粘贴&提交"按钮（HWND=15273062）
    
    流程：
    1. 先让 prompt 生成（走测试1的流程）
    2. 调用 LLM 获取 response
    3. 粘贴到 response 文本区
    4. 点击"粘贴&提交"按钮
    5. 观察 response.txt 是否被写入
    6. 观察 REPL 是否处理
    
    验证方法：写 response.txt → 点击按钮 → 检查文件是否被读取
    """
    print('\n' + '='*60)
    print('测试2：粘贴&提交按钮')
    print('='*60)
    
    win, controls = get_controls()
    
    # 检查 response.txt 当前内容
    resp_path = os.path.join(IO_DIR, 'response.txt')
    before_content = open(resp_path, encoding='utf-8').read() if os.path.exists(resp_path) else ''
    print(f'[response.txt 当前内容] {len(before_content)} chars')
    
    # 模拟 LLM response
    llm_response = '{"think": "测试", "action": "final", "answer": "测试结果"}'
    
    # 写入 response.txt（模拟我们手动写）
    open(resp_path, 'w', encoding='utf-8').write(llm_response)
    print(f'[写入] response.txt 已写入 {len(llm_response)} chars')
    
    # 粘贴到 response 文本区（HWND=28838998）
    resp_input = [c for c in win.children() if c.handle == 28838998][0]
    resp_input.click_input()
    time.sleep(0.3)
    kb.send_keys('^a')
    time.sleep(0.1)
    kb.send_keys('{DELETE}')
    time.sleep(0.1)
    
    subprocess.run(['powershell', '-Command', f'Set-Clipboard -Value "{llm_response}"'], capture_output=True)
    time.sleep(0.3)
    kb.send_keys('^v')
    time.sleep(0.5)
    
    resp_text = resp_input.window_text()
    print(f'[UI Response 文本区] 粘贴后长度={len(resp_text)} chars')
    print(f'内容预览: {resp_text[:100]}')
    
    # 点击"粘贴&提交"按钮
    submit_btn = [c for c in win.children() if c.handle == 15273062][0]
    print(f'[点击] 粘贴&提交按钮 HWND={submit_btn.handle}')
    submit_btn.click_input()
    
    # 等待 REPL 处理
    print('[等待] 8秒...')
    time.sleep(8)
    
    # 检查 response.txt 是否被清空（如果 REPL 读了，应该会清空或处理）
    after_content = open(resp_path, encoding='utf-8').read()
    print(f'\n[response.txt 处理后] {len(after_content)} chars')
    if after_content != before_content:
        print('[变化] response.txt 已被处理')
    else:
        print('[未变化] response.txt 未被处理')
    
    # 检查 final_answer.txt
    final_path = os.path.join(IO_DIR, 'final_answer.txt')
    if os.path.exists(final_path) and os.path.getsize(final_path) > 0:
        final_content = open(final_path, encoding='utf-8').read().strip()
        print(f'[final_answer.txt] {final_content[:200]}')
    
    show_io()


# ============ 测试3：检查"粘贴&提交"按钮是否真的通知了 REPL ============

def test_submit_vs_repl():
    """
    测试提交按钮是否真的触发了 REPL 处理
    
    方案：写入 response.txt → 点击按钮 → 观察 prompt.txt 是否更新
    如果 prompt.txt 持续更新，说明 REPL 在处理
    """
    print('\n' + '='*60)
    print('测试3：提交按钮触发 REPL 处理')
    print('='*60)
    
    win, controls = get_controls()
    
    # 检查当前 prompt.txt
    prompt_path = os.path.join(IO_DIR, 'prompt.txt')
    prompt_before = open(prompt_path, encoding='utf-8').read().strip() if os.path.exists(prompt_path) and os.path.getsize(prompt_path) > 0 else ''
    print(f'[prompt.txt 当前] {len(prompt_before)} chars')
    
    # 写一个 response
    llm_response = '{"think": "测试提交触发", "action": "final", "answer": "测试通过"}'
    resp_path = os.path.join(IO_DIR, 'response.txt')
    open(resp_path, 'w', encoding='utf-8').write(llm_response)
    
    # 粘贴到 response 区
    resp_input = [c for c in win.children() if c.handle == 28838998][0]
    resp_input.click_input()
    time.sleep(0.2)
    kb.send_keys('^a')
    time.sleep(0.1)
    kb.send_keys('{DELETE}')
    subprocess.run(['powershell', '-Command', f'Set-Clipboard -Value "{llm_response}"'], capture_output=True)
    time.sleep(0.3)
    kb.send_keys('^v')
    time.sleep(0.5)
    
    # 点击提交
    submit_btn = [c for c in win.children() if c.handle == 15273062][0]
    submit_btn.click_input()
    print('[点击] 已点击提交')
    
    # 轮询 prompt.txt 5次，每次 2 秒
    for i in range(5):
        time.sleep(2)
        prompt_now = open(prompt_path, encoding='utf-8').read().strip()
        if prompt_now != prompt_before:
            print(f'[{i*2}s] prompt.txt 有变化！长度={len(prompt_now)}')
            print(f'新内容预览: {prompt_now[:100]}')
            break
        else:
            print(f'[{i*2}s] prompt.txt 无变化')


# ============ 测试4：按钮坐标复核 ============

def verify_buttons():
    """重新确认所有按钮的实际 HWND 和位置"""
    print('\n' + '='*60)
    print('测试4：按钮控件坐标复核')
    print('='*60)
    
    win, controls = get_controls()
    
    print('按钮列表：')
    for c in win.children():
        try:
            if 'Button' in str(c.class_name):
                r = c.rectangle()
                # 通过位置判断按钮类型
                if r.left == 80 and r.top == 290:
                    label = '开始任务'
                elif r.left == 886 and r.top == 1522:
                    label = '粘贴&提交'
                elif r.left == 886 and r.top == 788:
                    label = '复制prompt(?)'
                elif r.left == 886 and r.top == 1588:
                    label = '清空日志(?)'
                elif r.left == 80 and r.top == 1580:
                    label = '新任务'
                elif r.left == 80 and r.top == 1498:
                    label = '打断(?)'
                else:
                    label = '未知'
                print(f'  [{label}] HWND={c.handle} L={r.left},T={r.top},R={r.right},B={r.bottom}')
        except:
            pass


# ============ 主测试入口 ============

if __name__ == '__main__':
    print('='*60)
    print('MyAgent UI 控件测试')
    print('='*60)
    
    # 等待用户准备好
    print('\n确认 MyAgent UI 已启动（PID 18012）')
    print('io/ 目录:', IO_DIR)
    print('[开始] 10秒后自动开始测试...')
    time.sleep(10)
    
    verify_buttons()
    test_start_button()
    test_submit_button()
    test_submit_vs_repl()
    
    print('\n' + '='*60)
    print('测试完成')
    print('='*60)
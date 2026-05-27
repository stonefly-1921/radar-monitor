"""
MyAgent UI 自动化 - 固化测试流程
===============================

目的：通过 UI 控件操作 MyAgent，完成端到端自动化测试

操作流程（不走文件，直接用控件）：
1. 在任务输入框（HWND=13700270）输入任务
2. 点击开始任务（HWND=265380）
3. 等待 prompt.txt 有内容（REPL 生成）
4. 读取 prompt.txt 内容，发给 LLM
5. 在 response 文本区（HWND=28838998）粘贴 LLM 回复
6. 点击粘贴&提交（HWND=15273062）
7. 等待 REPL 处理，重复直到完成

关键发现（来自 test_ui_controls.py）：
- input.txt 不会直接被写入，开始任务是通过 stdin 通知 REPL
- prompt.txt 由 REPL 生成，但 UI 的 prompt 文本区要等 _poll_io_files 更新
- 提交后 response.txt 会被 REPL 读取，但只读一次然后清空
"""
import sys, os, time, json, subprocess, urllib.request
from pywinauto import Application
import pywinauto.keyboard as kb

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'
IO_DIR = os.path.join(MYAGENT_DIR, 'io')


# ============ 工具函数 ============

def get_api_key():
    result = subprocess.run(
        ['powershell', '-Command', '[Environment]::GetEnvironmentVariable("MINIMAX_API_KEY", "User")'],
        capture_output=True, text=True, encoding='utf-8'
    )
    return result.stdout.strip()


def get_win():
    app = Application(backend='win32').connect(process=18012)
    return app.window(title='MyAgent v2.1')


def find_control(win, hwnd):
    for c in win.children():
        if c.handle == hwnd:
            return c
    return None


def ui_input_text(win, hwnd, text):
    """通过 UI 输入文本到控件"""
    ctrl = find_control(win, hwnd)
    if not ctrl:
        return False
    ctrl.click_input()
    time.sleep(0.3)
    kb.send_keys('^a')
    time.sleep(0.1)
    kb.send_keys('{DELETE}')
    time.sleep(0.1)
    
    # 设置剪贴板并粘贴（分段）
    for i in range(0, len(text), 500):
        chunk = text[i:i+500]
        subprocess.run(
            ['powershell', '-Command', f'Set-Clipboard -Value "{chunk}"'],
            capture_output=True
        )
        time.sleep(0.3)
        kb.send_keys('^v')
        time.sleep(0.3)
    
    return True


def click_button(win, hwnd):
    """点击按钮"""
    btn = find_control(win, hwnd)
    if btn:
        btn.click_input()
        return True
    return False


def read_file(path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return open(path, encoding='utf-8').read().strip()
    return ''


def wait_for_file(path, timeout=30, min_size=10):
    """等待文件出现内容"""
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(path) and os.path.getsize(path) >= min_size:
            content = open(path, encoding='utf-8').read().strip()
            if content:
                return content
        time.sleep(1)
    return None


# ============ LLM 调用 ============

def call_llm(prompt_text: str) -> dict:
    """调用 LLM，返回解析后的 JSON dict"""
    api_key = get_api_key()
    if not api_key:
        print('[LLM] API key 未找到')
        return None
    
    url = 'https://api.minimaxi.com/anthropic/v1/messages'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'anthropic-version': '2023-06-01',
    }
    
    payload = {
        'model': 'MiniMax-M2.7',
        'messages': [{'role': 'user', 'content': prompt_text}],
        'max_tokens': 8192,
        'temperature': 0.7
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            for item in result.get('content', []):
                if item.get('type') == 'text':
                    text = item.get('text', '').strip()
                    if text:
                        try:
                            return json.loads(text)
                        except:
                            return {'action': 'final', 'answer': text}
            return None
    except Exception as e:
        print(f'[LLM] 调用失败: {e}')
        return None


# ============ 核心自动化循环 ============

def run_task(task: str, max_turns=20):
    """完整的多轮 UI 自动化流程"""
    
    print('='*60)
    print('MyAgent UI 自动化')
    print('='*60)
    print(f'任务: {task[:50]}...')
    
    win = get_win()
    
    # ---- 步骤1：输入任务 ----
    print('\n[Step 1] 输入任务到 UI...')
    ok = ui_input_text(win, 13700270, task)
    if ok:
        print('  输入成功')
    
    # ---- 步骤2：点击开始任务 ----
    print('[Step 2] 点击开始任务...')
    click_button(win, 265380)
    print('  已点击')
    
    # ---- 步骤3：等待 prompt 生成 ----
    print('[Step 3] 等待 prompt 生成...')
    prompt_path = os.path.join(IO_DIR, 'prompt.txt')
    prompt_content = wait_for_file(prompt_path, timeout=30)
    
    if not prompt_content:
        print('[错误] prompt 生成超时')
        return None
    
    print(f'  prompt 生成完成，长度={len(prompt_content)}')
    
    # ---- 多轮循环 ----
    current_prompt = prompt_content
    last_prompt_len = len(prompt_content)
    
    for turn in range(1, max_turns + 1):
        print(f'\n--- Turn {turn} ---')
        
        # 发给 LLM
        print('[LLM] 调用...')
        llm_result = call_llm(current_prompt)
        
        if not llm_result:
            print('[错误] LLM 调用失败')
            break
        
        print(f'[LLM] action={llm_result.get("action", "?")}')
        
        # 把 LLM 的文本回复转成 JSON 字符串
        response_json = json.dumps(llm_result, ensure_ascii=False)
        
        # ---- 步骤4：粘贴 response 到 UI ----
        print('[Step 4] 粘贴 response 到 UI...')
        ok = ui_input_text(win, 28838998, response_json)
        if ok:
            print('  粘贴成功')
        
        # ---- 步骤5：点击提交 ----
        print('[Step 5] 点击粘贴&提交...')
        click_button(win, 15273062)
        print('  已点击提交')
        
        # ---- 步骤6：等待 REPL 处理 ----
        print('[Step 6] 等待 REPL 处理...')
        time.sleep(8)
        
        # 检查最终答案
        final_path = os.path.join(IO_DIR, 'final_answer.txt')
        if os.path.exists(final_path) and os.path.getsize(final_path) > 0:
            final_content = open(final_path, encoding='utf-8').read().strip()
            if final_content:
                print(f'\n[完成] 最终答案: {final_content[:300]}')
                return final_content
        
        # 检查新 prompt
        new_prompt = read_file(prompt_path)
        if new_prompt and len(new_prompt) != last_prompt_len:
            # 有新内容，说明 REPL 在继续
            current_prompt = new_prompt
            last_prompt_len = len(current_prompt)
            print(f'[REPL] 继续运行，新 prompt 长度={len(current_prompt)}')
        else:
            # 没有新 prompt，检查 response.txt 是否被清空（说明 REPL 读了）
            resp_path = os.path.join(IO_DIR, 'response.txt')
            resp_size = os.path.getsize(resp_path) if os.path.exists(resp_path) else 0
            if resp_size == 0:
                print('[REPL] response.txt 已被读取，继续')
                # response.txt 被清空说明 REPL 读到了，可以继续发下一个
            else:
                print(f'[REPL] response.txt 仍有 {resp_size} bytes，未处理')
                # 如果 response.txt 没被清空，REPL 可能卡住了
    
    print('\n[超时] 达到最大轮次')
    return None


# ============ 入口 ============

if __name__ == '__main__':
    # 先清空 io/
    for f in ['input.txt', 'response.txt', 'tool_result.json', 'final_answer.txt']:
        path = os.path.join(IO_DIR, f)
        if os.path.exists(path):
            open(path, 'w', encoding='utf-8').write('')
    print('[准备] io/ 已清空')
    
    task = '请计算 1+1 等于几'
    result = run_task(task)
    
    print('\n' + '='*60)
    print(f'最终结果: {result}')
    print('='*60)
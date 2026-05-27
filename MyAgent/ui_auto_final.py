"""
MyAgent UI 自动化 - 完整多轮流程
修复：直接写 response.txt + 点击按钮提交
"""
import sys, os, time, json, subprocess, urllib.request
from pywinauto import Application
import pywinauto.keyboard as kb

# ============ LLM 调用 ============
def get_api_key():
    result = subprocess.run(
        ['powershell', '-Command', '[Environment]::GetEnvironmentVariable("MINIMAX_API_KEY", "User")'],
        capture_output=True, text=True, encoding='utf-8'
    )
    return result.stdout.strip()

def call_llm(prompt: str) -> str:
    api_key = get_api_key()
    url = 'https://api.minimaxi.com/anthropic/v1/messages'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'anthropic-version': '2023-06-01',
    }
    payload = {
        'model': 'MiniMax-M2.7',
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': 8192,
        'temperature': 0.7
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        for item in result.get('content', []):
            if item.get('type') == 'text':
                return item.get('text', '')
    return None

# ============ 连接 UI ============
def get_win():
    app = Application(backend='win32').connect(process=18012)
    return app.window(title='MyAgent v2.1')

def find(win, hwnd):
    for c in win.children():
        if c.handle == hwnd:
            return c
    return None

# ============ 写 response.txt 并点击提交 ============
def submit_response_json(win, json_str: str):
    io_dir = r'C:\Users\15041\.openclaw\workspace\MyAgent\io'
    resp_file = os.path.join(io_dir, 'response.txt')
    
    # 方案A：直接写 response.txt（绕过 UI 控件）
    open(resp_file, 'w', encoding='utf-8').write(json_str)
    print(f'  [方案A] 直接写入 response.txt ({len(json_str)} chars)')
    
    # 同时尝试通过 UI 粘贴（双保险）
    resp_input = find(win, 28838998)  # response 文本区
    if resp_input:
        resp_input.click_input()
        time.sleep(0.3)
        kb.send_keys('^a')
        time.sleep(0.1)
        kb.send_keys('{DELETE}')
        time.sleep(0.1)
        
        # 分段粘贴
        for i in range(0, len(json_str), 1000):
            chunk = json_str[i:i+1000]
            chunk_clean = chunk.replace('"', '"').replace('{', '{').replace('}', '}')
            subprocess.run(['powershell', '-Command', f'Set-Clipboard -Value "{chunk_clean}"'], capture_output=True)
            time.sleep(0.3)
            kb.send_keys('^v')
            time.sleep(0.3)
        
        print('  [UI] 已粘贴到 response 文本区')
    
    # 点击提交按钮（HWND=15273062）
    submit_btn = find(win, 15273062)
    if submit_btn:
        submit_btn.click_input()
        print('  [UI] 已点击提交按钮')
    else:
        # 备用：用键盘 Alt+S 快捷键
        print('  [备用] 按钮未找到，尝试键盘快捷键')
        kb.send_keys('^{ENTER}')  # Ctrl+Enter 触发提交

# ============ 主流程 ============
def run(task: str, max_turns=15):
    io_dir = r'C:\Users\15041\.openclaw\workspace\MyAgent\io'
    print('='*60)
    print('MyAgent UI 自动化')
    print('='*60)
    
    # 连接 UI
    print('[连接] MyAgent UI')
    win = get_win()
    
    # 输入任务
    print('[输入] 任务...')
    task_input = find(win, 13700270)
    if task_input:
        task_input.click_input()
        time.sleep(0.3)
        kb.send_keys('^a')
        time.sleep(0.1)
        kb.send_keys('{DELETE}')
        subprocess.run(['powershell', '-Command', f'Set-Clipboard -Value "{task}"'], capture_output=True)
        time.sleep(0.3)
        kb.send_keys('^v')
        time.sleep(0.5)
        print(f'  已输入任务 ({len(task)} chars)')
    
    # 点击开始
    start_btn = find(win, 265380)
    if start_btn:
        start_btn.click_input()
        print('[开始] 已点击开始任务')
    
    # 等待 prompt 生成
    print('[等待] prompt 生成...')
    prompt_file = os.path.join(io_dir, 'prompt.txt')
    for _ in range(30):
        if os.path.exists(prompt_file) and os.path.getsize(prompt_file) > 100:
            break
        time.sleep(1)
    else:
        print('[错误] prompt 生成超时')
        return
    
    # 多轮循环
    current_prompt = open(prompt_file, encoding='utf-8').read().strip()
    print(f'[Prompt] 长度={len(current_prompt)}')
    
    for turn in range(1, max_turns+1):
        print(f'\n--- Turn {turn} ---')
        
        # 调用 LLM
        print('[LLM] 调用...')
        response = call_llm(current_prompt)
        if not response:
            print('[错误] LLM 调用失败')
            break
        
        print(f'[LLM] 回复: {response[:100]}...')
        
        # 解析
        try:
            data = json.loads(response)
        except:
            print('[错误] 非 JSON 响应')
            break
        
        action = data.get('action', '')
        
        if action == 'final':
            # 最终答案 - 直接写 response.txt + 点击提交
            print(f'[最终] 提交: {data.get("answer", "")[:100]}')
            submit_response_json(win, response)
            time.sleep(5)
            
            # 检查 final_answer.txt
            final_file = os.path.join(io_dir, 'final_answer.txt')
            if os.path.exists(final_file) and os.path.getsize(final_file) > 0:
                ans = open(final_file, encoding='utf-8').read().strip()
                print(f'\n[完成] 最终答案: {ans[:300]}')
                return ans
            else:
                print(f'[完成] LLM 直接回答: {data.get("answer", "")[:200]}')
                return data.get('answer', '')
        
        else:
            # 有工具调用 - 提交 response
            print(f'[工具调用] 提交 LLM 回复 ({len(response)} chars)')
            submit_response_json(win, response)
            time.sleep(8)
            
            # 读取新 prompt
            for _ in range(15):
                if os.path.exists(prompt_file):
                    new_prompt = open(prompt_file, encoding='utf-8').read().strip()
                    if new_prompt and new_prompt != current_prompt:
                        current_prompt = new_prompt
                        print(f'[新 Prompt] 长度={len(current_prompt)}，继续')
                        break
                time.sleep(1)
            
            # 检查 final_answer
            final_file = os.path.join(io_dir, 'final_answer.txt')
            if os.path.exists(final_file) and os.path.getsize(final_file) > 0:
                ans = open(final_file, encoding='utf-8').read().strip()
                print(f'\n[完成] 最终答案: {ans[:300]}')
                return ans
    
    return None

if __name__ == '__main__':
    task = '请计算 1+1 等于几'
    result = run(task)
    print('\n' + '='*60)
    print(f'结果: {result}')
    print('='*60)
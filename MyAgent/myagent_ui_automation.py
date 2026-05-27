"""
MyAgent UI 自动化测试 - 固化流程
==================================

目的：用 UI 控件操作 MyAgent，完成端到端自动化测试

流程：
1. 连接 UI 窗口（PID 18012）
2. 通过控件输入任务（Ctrl+A 全选 + Ctrl+V 粘贴）
3. 点击开始任务按钮
4. 轮询等待 prompt.txt 生成
5. 调用 LLM 获取 response
6. 通过控件粘贴 response 到 response 文本区
7. 点击"粘贴&提交"按钮
8. 等待 REPL 处理，重复直到 final_answer.txt 出现

关键控件（HWND）：
- 13700270：任务输入框
- 265380：开始任务按钮
- 28838998：response 文本区
- 15273062：粘贴&提交按钮
- 330868：prompt 文本区（只读）

LLM：MiniMax-M2.7 via https://api.minimaxi.com/anthropic/v1/messages
API Key：从 User 环境变量读取 MINIMAX_API_KEY
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


def find(win, hwnd):
    for c in win.children():
        if c.handle == hwnd:
            return c
    return None


def ui_paste(win, hwnd, text):
    """通过 UI 控件粘贴文本"""
    ctrl = find(win, hwnd)
    if not ctrl:
        print(f'  [错误] 控件 {hwnd} 未找到')
        return False
    
    ctrl.click_input()
    time.sleep(0.3)
    
    # 清空
    kb.send_keys('^a')
    time.sleep(0.1)
    kb.send_keys('{DELETE}')
    time.sleep(0.1)
    
    # 分段粘贴（避免一次性粘贴丢失中文）
    for i in range(0, len(text), 500):
        chunk = text[i:i+500]
        try:
            subprocess.run(
                ['powershell', '-Command', f'Set-Clipboard -Value "{chunk}"'],
                capture_output=True, timeout=5
            )
        except:
            pass
        time.sleep(0.3)
        kb.send_keys('^v')
        time.sleep(0.3)
    
    return True


def click_btn(win, hwnd):
    btn = find(win, hwnd)
    if btn:
        btn.click_input()
        return True
    return False


def wait_file(path, timeout=30, min_size=100):
    """等待文件出现内容"""
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(path):
            try:
                size = os.path.getsize(path)
                if size >= min_size:
                    content = open(path, encoding='utf-8').read().strip()
                    if content:
                        return content
            except:
                pass
        time.sleep(1)
    return None


def call_llm(prompt_text: str) -> dict:
    """调用 LLM，返回 dict"""
    api_key = get_api_key()
    if not api_key:
        print('  [LLM] API key 未找到')
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
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            for item in result.get('content', []):
                if item.get('type') == 'text':
                    text = item.get('text', '').strip()
                    if text:
                        try:
                            return json.loads(text)
                        except:
                            return {'action': 'final', 'answer': text}
    except Exception as e:
        print(f'  [LLM] 失败: {e}')
    return None


def clean_io():
    """清空 io 关键文件"""
    for f in ['input.txt', 'response.txt', 'tool_result.json', 'final_answer.txt']:
        path = os.path.join(IO_DIR, f)
        if os.path.exists(path):
            try:
                open(path, 'w', encoding='utf-8').write('')
            except:
                pass


def show_io(label=''):
    """打印 io 文件状态"""
    if label:
        print(f'  [{label}]')
    for f in ['input.txt', 'prompt.txt', 'response.txt', 'final_answer.txt']:
        path = os.path.join(IO_DIR, f)
        if os.path.exists(path):
            size = os.path.getsize(path)
            content = open(path, encoding='utf-8').read().strip()[:60] if size > 0 else ''
            print(f'    {f}: {size}B | {content}')


# ============ 核心流程 ============

def run(task: str, max_turns=20):
    """完整的多轮 UI 自动化流程"""
    
    print('='*60)
    print('MyAgent UI 自动化')
    print('='*60)
    print(f'Task: {task[:50]}...')
    
    # 清空
    clean_io()
    
    # 连接 UI
    print('[连接] MyAgent UI...')
    win = get_win()
    print('  连接成功')
    
    # 步骤1：输入任务到 UI
    print('[输入] 任务到 UI...')
    ui_paste(win, 13700270, task)
    print('  输入完成')
    
    # 步骤2：点击开始任务
    print('[开始] 点击开始任务...')
    click_btn(win, 265380)
    print('  点击完成')
    
    # 步骤3：等待 prompt 生成
    print('[等待] prompt 生成...')
    prompt_path = os.path.join(IO_DIR, 'prompt.txt')
    prompt = wait_file(prompt_path, timeout=30)
    if not prompt:
        print('  [失败] prompt 生成超时')
        return None
    print(f'  prompt 生成: {len(prompt)} chars')
    
    current_prompt = prompt
    last_prompt_len = len(prompt)
    
    # 多轮循环
    for turn in range(1, max_turns + 1):
        print(f'\n[Turn {turn}]')
        
        # 调用 LLM
        print('[LLM] 调用...')
        result = call_llm(current_prompt)
        if not result:
            print('  [失败] LLM 调用失败')
            break
        
        action = result.get('action', '')
        print(f'  action={action}')
        
        # 构造 JSON 字符串
        response_json = json.dumps(result, ensure_ascii=False)
        
        # 粘贴 response 到 UI
        print('[粘贴] response 到 UI...')
        ui_paste(win, 28838998, response_json)
        print('  粘贴完成')
        
        # 点击提交
        print('[提交] 点击提交按钮...')
        click_btn(win, 15273062)
        print('  点击完成')
        
        # 等待 REPL 处理
        print('[等待] REPL 处理 (8s)...')
        time.sleep(8)
        
        # 检查 final_answer
        final_path = os.path.join(IO_DIR, 'final_answer.txt')
        if os.path.exists(final_path) and os.path.getsize(final_path) > 0:
            final_content = open(final_path, encoding='utf-8').read().strip()
            if final_content:
                print(f'\n[完成] final_answer: {final_content[:200]}')
                return final_content
        
        # 检查新 prompt
        new_prompt = ''
        try:
            if os.path.exists(prompt_path) and os.path.getsize(prompt_path) > 0:
                new_prompt = open(prompt_path, encoding='utf-8').read().strip()
        except:
            pass
        
        if new_prompt and len(new_prompt) != last_prompt_len:
            # prompt 有变化，REPL 产生了新内容，继续
            current_prompt = new_prompt
            last_prompt_len = len(current_prompt)
            print(f'  [REPL] 新 prompt ({len(current_prompt)} chars)，继续')
        else:
            # prompt 没变化，检查 response.txt 是否被清空
            resp_path = os.path.join(IO_DIR, 'response.txt')
            resp_size = os.path.getsize(resp_path) if os.path.exists(resp_path) else 0
            if resp_size > 0 and '计算' in open(resp_path, encoding='utf-8').read():
                # response.txt 还有我们写的任务内容，说明还没被读
                print(f'  [REPL] response.txt 未被读取 ({resp_size}B)，重试')
                continue
            else:
                print(f'  [REPL] 无新 prompt，response.txt={resp_size}B')
    
    print('[超时] 达到最大轮次')
    return None


# ============ 入口 ============

if __name__ == '__main__':
    task = '请计算 1+1 等于几'
    result = run(task)
    print('\n' + '='*60)
    print(f'结果: {result}')
    print('='*60)
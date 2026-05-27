"""
MyAgent UI 自动化 - 固化测试流程 v2
=====================================

核心发现：
1. "开始任务" 按钮 → UI 通过 stdin pipe 发任务给 REPL → REPL 生成 prompt.txt
2. "粘贴&提交" 按钮 → UI 发送 newline 到 REPL stdin → REPL 读 response.txt 处理
3. response.txt 被 REPL 读走后清空（0 字节），说明 REPL 确实处理了
4. REPL 处理完后可能：生成新 prompt.txt（继续） 或 写 final_answer.txt（结束）

自动化流程：
1. 连接 UI
2. 输入任务到 UI 输入框（HWND=13700270）
3. 点击开始任务（HWND=265380）
4. 轮询等待 prompt.txt 生成
5. 调用 LLM 获取 response
6. 写 response.txt
7. 点击粘贴&提交（HWND=15273062）→ 触发 newline → REPL 读 response.txt
8. 等待 REPL 处理（8秒）
9. 检查 final_answer.txt 或新 prompt.txt
10. 重复直到完成
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
    """通过 UI 控件粘贴文本（Ctrl+A 全选 + Ctrl+V 粘贴）"""
    ctrl = find(win, hwnd)
    if not ctrl:
        print(f'  [错误] 控件 {hwnd} 未找到')
        return False
    
    ctrl.click_input()
    time.sleep(0.3)
    kb.send_keys('^a')
    time.sleep(0.1)
    kb.send_keys('{DELETE}')
    time.sleep(0.1)
    
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
    """等待文件出现内容（且内容不为空）"""
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
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST'
    )
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
            content = open(path, encoding='utf-8').read().strip()[:80] if size > 0 else ''
            print(f'    {f}: {size}B | {content}')
        else:
            print(f'    {f}: (不存在)')


# ============ 核心流程 ============

def run(task: str, max_turns=20):
    """完整的多轮 UI 自动化流程"""
    
    print('='*60)
    print('MyAgent UI 自动化 v2')
    print('='*60)
    print(f'Task: {task[:50]}...')
    
    # 清空
    clean_io()
    
    # 连接 UI
    print('[连接] MyAgent UI...')
    win = get_win()
    print('  连接成功')
    
    # ===== 步骤1：输入任务到 UI =====
    print('\n[Step 1] 输入任务到 UI...')
    ui_paste(win, 13700270, task)
    print('  输入完成')
    
    # ===== 步骤2：点击开始任务 =====
    print('[Step 2] 点击开始任务...')
    click_btn(win, 265380)
    print('  点击完成')
    
    # ===== 步骤3：等待 prompt 生成 =====
    print('[Step 3] 等待 prompt 生成...')
    prompt_path = os.path.join(IO_DIR, 'prompt.txt')
    prompt = wait_file(prompt_path, timeout=30)
    if not prompt:
        print('  [失败] prompt 生成超时')
        return None
    print(f'  prompt 生成: {len(prompt)} chars')
    
    current_prompt = prompt
    last_prompt_len = len(prompt)
    
    # ===== 多轮循环 =====
    for turn in range(1, max_turns + 1):
        print(f'\n=== Turn {turn} ===')
        
        # ---- 调用 LLM ----
        print('[LLM] 调用...')
        result = call_llm(current_prompt)
        if not result:
            print('  [失败] LLM 调用失败')
            break
        
        action = result.get('action', '')
        print(f'  action={action}')
        
        # 构造 JSON 字符串
        response_json = json.dumps(result, ensure_ascii=False)
        
        # ---- 写 response.txt（绕过 UI，直接写文件）----
        # 这样更可靠：REPL 读文件，不依赖 UI 控件
        print('[写文件] 写入 response.txt...')
        resp_path = os.path.join(IO_DIR, 'response.txt')
        open(resp_path, 'w', encoding='utf-8').write(response_json)
        print(f'  已写入 {len(response_json)} chars')
        
        # ---- 同时粘贴到 UI 的 response 文本区（双保险）----
        print('[粘贴] 粘贴到 UI response 区...')
        ui_paste(win, 28838998, response_json)
        print('  粘贴完成')
        
        # ---- 点击"粘贴&提交"按钮：触发 newline 到 REPL stdin ----
        print('[提交] 点击粘贴&提交按钮...')
        click_btn(win, 15273062)
        print('  已点击，REPL 将收到 newline 信号')
        
        # ---- 等待 REPL 处理 ----
        print('[等待] REPL 处理 (10s)...')
        time.sleep(10)
        
        # ---- 检查 final_answer ----
        final_path = os.path.join(IO_DIR, 'final_answer.txt')
        if os.path.exists(final_path) and os.path.getsize(final_path) > 0:
            final_content = open(final_path, encoding='utf-8').read().strip()
            if final_content:
                print(f'\n[完成] final_answer: {final_content[:300]}')
                return final_content
        
        # ---- 检查 response.txt 是否被 REPL 读取（应该被清空了）----
        resp_size = os.path.getsize(resp_path) if os.path.exists(resp_path) else 0
        if resp_size > 0:
            print(f'  [警告] response.txt 仍有 {resp_size}B，REPL 可能没读到')
        else:
            print('  [REPL] response.txt 已读取（被清空）')
        
        # ---- 检查 prompt.txt 是否有新内容 ----
        try:
            new_prompt = ''
            if os.path.exists(prompt_path) and os.path.getsize(prompt_path) > 0:
                new_prompt = open(prompt_path, encoding='utf-8').read().strip()
            
            if new_prompt and len(new_prompt) != last_prompt_len:
                # prompt 有变化，REPL 产生了新内容，继续
                current_prompt = new_prompt
                last_prompt_len = len(current_prompt)
                print(f'  [REPL] 新 prompt ({len(current_prompt)} chars)，继续下一轮')
            else:
                print(f'  [REPL] prompt 无变化，继续等...')
        except Exception as e:
            print(f'  [错误] {e}')
    
    print('[超时] 达到最大轮次')
    return None


# ============ 入口 ============

if __name__ == '__main__':
    task = '请计算 1+1 等于几'
    result = run(task)
    print('\n' + '='*60)
    print(f'最终结果: {result}')
    print('='*60)
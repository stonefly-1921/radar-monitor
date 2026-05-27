"""
MyAgent UI 自动化测试 - 完整流程

目标：让 MyAgent 通过 UI 界面完成任务，模拟人工操作流程：
1. 启动 MyAgent UI（调用 start() 启动 REPL 子进程）
2. 操作 UI：输入任务 → 点击开始 → 等待 prompt 生成
3. 复制 prompt → 调用 LLM → 得到 response
4. 粘贴 response → 点击提交 → 等待工具执行
5. 重复直到完成

核心：必须走 UI 的 REPL 子进程（loop_v2.py），不能直接写文件
"""
import sys, os, time, json, urllib.request, subprocess

# ============ LLM 调用 ============

def call_llm(messages: list, model: str = "MiniMax-M2.7") -> str:
    api_key = os.environ.get("MINIMAX_API_KEY", "")
    if not api_key:
        # 尝试从注册表读取（User 级别环境变量）
        try:
            import subprocess
            result = subprocess.run(
                ['powershell', '-Command', "[Environment]::GetEnvironmentVariable('MINIMAX_API_KEY', 'User')"],
                capture_output=True, text=True, encoding='utf-8'
            )
            api_key = result.stdout.strip()
        except:
            pass
    
    if not api_key:
        print("[LLM] API key 未配置，请设置 MINIMAX_API_KEY 环境变量")
        return None
    
    url = "https://api.minimaxi.com/anthropic/v1/messages"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    payload = {"model": model, "messages": messages, "max_tokens": 8192, "temperature": 0.7}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result["content"][0]["text"]
    except Exception as e:
        print(f"[LLM ERROR] {e}")
        return None


# ============ UI 启动（关键：正确启动 REPL 子进程）============

def launch_myagent_ui():
    """启动 MyAgent UI 并确保 REPL 子进程运行。"""
    from pywinauto import Application
    import threading
    
    # 检查是否已有进程
    try:
        app = Application(backend="win32").connect(process=18012)
        win = app.window(title="MyAgent v2.1")
        print("[UI] 发现已有 MyAgent 进程")
        return win
    except:
        pass
    
    # 启动 UI（通过 subprocess 启动 loop_v2.py REPL）
    myagent_dir = os.path.dirname(os.path.abspath(__file__))
    ui_path = os.path.join(myagent_dir, "agent", "ui.py")
    
    # 用 pythonw 启动（后台运行）
    proc = subprocess.Popen(
        [sys.executable, ui_path],
        cwd=myagent_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8'
    )
    
    # 等待窗口出现
    print("[UI] 等待 MyAgent 窗口启动...")
    time.sleep(5)
    
    # 连接
    app = Application(backend="win32").connect(title="MyAgent v2.1", timeout=15)
    win = app.window(title="MyAgent v2.1")
    print(f"[UI] 窗口已连接")
    
    return win


def get_all_controls(win):
    """返回所有子控件的 HWND->rect 映射。"""
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
    return controls


def find_control_by_pos(controls, l, t, r, b, tol=3):
    """根据坐标找控件。"""
    for hwnd, info in controls.items():
        rect = info['rect']
        if (abs(rect[0]-l) <= tol and abs(rect[1]-t) <= tol and
            abs(rect[2]-r) <= tol and abs(rect[3]-b) <= tol):
            return info['obj'], hwnd
    return None, None


# ============ 核心操作函数 ============

def write_task_via_ui(win, task_text):
    """
    通过 UI 输入任务：点击输入框 → 全选清空 → 输入内容
    然后点击开始任务按钮
    """
    import pywinauto.keyboard as kb
    
    controls = get_all_controls(win)
    
    # 找任务输入框（坐标 L=80,T=172,R=858,B=282，HWND=13700270）
    task_input, task_hwnd = find_control_by_pos(controls, 80, 172, 858, 282)
    if not task_input:
        task_input = [c for c in win.children() if c.handle == 13700270][0]
    
    print(f"[UI] 点击任务输入框 HWND={task_input.handle}")
    task_input.click_input()
    time.sleep(0.3)
    
    # 清空现有内容
    kb.send_keys('^a')
    time.sleep(0.1)
    kb.send_keys('{DELETE}')
    time.sleep(0.1)
    
    # 输入任务（分段输入，防止长文本丢字）
    chunk_size = 50
    for i in range(0, len(task_text), chunk_size):
        kb.send_keys(task_text[i:i+chunk_size])
        time.sleep(0.2)
    
    time.sleep(0.5)
    print(f"[UI] 已输入任务，长度={len(task_text)}")
    
    # 点击开始任务按钮（HWND=265380）
    start_btn, start_hwnd = find_control_by_pos(controls, 80, 290, 858, 358)
    if not start_btn:
        start_btn = [c for c in win.children() if c.handle == 265380][0]
    
    print(f"[UI] 点击开始任务 HWND={start_btn.handle}")
    start_btn.click_input()


def wait_for_prompt_file(io_dir, timeout=30):
    """等待 prompt.txt 出现内容。"""
    prompt_file = os.path.join(io_dir, "prompt.txt")
    start = time.time()
    last_size = 0
    while time.time() - start < timeout:
        if os.path.exists(prompt_file):
            size = os.path.getsize(prompt_file)
            if size > 0:
                content = open(prompt_file, encoding='utf-8').read().strip()
                if content:
                    print(f"[UI] prompt 生成完成，长度={len(content)}")
                    return content
            if size != last_size:
                print(f"[UI] prompt 生成中... {size} bytes")
                last_size = size
        time.sleep(1)
    print("[UI] prompt 生成超时")
    return None


def paste_and_submit_via_ui(win, response_text):
    """
    通过 UI 粘贴 response 并提交：
    1. 粘贴到 response 文本区
    2. 点击粘贴&提交按钮
    """
    import pywinauto.keyboard as kb
    
    controls = get_all_controls(win)
    
    # 找 response 文本区（坐标 L=886,T=900,R=2422,B=1516，HWND=28838998）
    resp_input, resp_hwnd = find_control_by_pos(controls, 886, 900, 2422, 1516)
    if not resp_input:
        resp_input = [c for c in win.children() if c.handle == 28838998][0]
    
    print(f"[UI] 点击 response 文本区 HWND={resp_input.handle}")
    resp_input.click_input()
    time.sleep(0.3)
    
    # 清空
    kb.send_keys('^a')
    time.sleep(0.1)
    kb.send_keys('{DELETE}')
    time.sleep(0.1)
    
    # 粘贴（先设置剪贴板）
    subprocess.run(['powershell', '-Command', f'Set-Clipboard -Value "{response_text[:5000]}"'], capture_output=True)
    time.sleep(0.3)
    kb.send_keys('^v')
    time.sleep(0.5)
    print(f"[UI] 已粘贴 response，长度={len(response_text)}")
    
    # 点击粘贴&提交按钮（HWND=15273062，坐标 L=886,T=1522,R=2456,B=1582）
    submit_btn, submit_hwnd = find_control_by_pos(controls, 886, 1522, 2456, 1582)
    if not submit_btn:
        submit_btn = [c for c in win.children() if c.handle == 15273062][0]
    
    print(f"[UI] 点击粘贴&提交 HWND={submit_btn.handle}")
    submit_btn.click_input()


def check_final_answer(io_dir):
    """检查 final_answer.txt"""
    final_file = os.path.join(io_dir, "final_answer.txt")
    if os.path.exists(final_file):
        content = open(final_file, encoding='utf-8').read().strip()
        if content:
            return content
    return None


def parse_llm_response(raw: str) -> dict:
    """解析 LLM JSON 回复。"""
    if not raw or not raw.strip():
        return {"action": "final", "content": "", "tool_calls": []}
    raw = raw.strip()
    if not raw.startswith('{'):
        return {"action": "final", "content": raw, "tool_calls": []}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"action": "final", "content": raw, "tool_calls": []}
    if 'think' in data and 'action' in data:
        if data['action'] == 'tool_call' and 'tools' in data:
            return {"action": "tool_call", "tool_calls": data['tools']}
        elif data['action'] == 'final':
            return {"action": "final", "content": data.get('answer', '')}
    if 'tool_calls' in data and data['tool_calls']:
        return {"action": "tool_call", "tool_calls": data['tool_calls']}
    return {"action": "final", "content": raw}


# ============ 主自动化流程 ============

def run_ui_automation(task: str, max_turns: int = 15):
    """完整的多轮 UI 自动化流程。"""
    
    myagent_dir = os.path.dirname(os.path.abspath(__file__))
    io_dir = os.path.join(myagent_dir, "io")
    
    # Step 1: 启动/连接 UI
    print("[Step 1] 连接 MyAgent UI...")
    win = launch_myagent_ui()
    print("[Step 1] UI 已就绪")
    
    # Step 2: 输入任务
    print("[Step 2] 输入任务...")
    write_task_via_ui(win, task)
    
    # Step 3: 等待 prompt 生成
    print("[Step 3] 等待 prompt 生成...")
    prompt = wait_for_prompt_file(io_dir, timeout=30)
    if not prompt:
        print("[错误] prompt 生成失败")
        return None
    
    # ========== 多轮循环 ==========
    turn = 0
    current_prompt = prompt
    
    while turn < max_turns:
        turn += 1
        print(f"\n{'='*60}")
        print(f"[Turn {turn}] 调用 LLM...")
        
        # 发给 LLM
        messages = [{"role": "user", "content": current_prompt}]
        response = call_llm(messages)
        if not response:
            print("[错误] LLM 调用失败")
            break
        
        print(f"[Turn {turn}] LLM 回复长度: {len(response)}")
        
        # 解析
        parsed = parse_llm_response(response)
        
        if parsed.get("action") == "final":
            # 最终答案 - 粘贴到 response 并提交
            print(f"[Turn {turn}] 最终答案，提交...")
            paste_and_submit_via_ui(win, response)
            time.sleep(3)
            
            final = check_final_answer(io_dir)
            if final:
                print(f"[完成] 任务完成！")
                return final
            else:
                return parsed.get("content", response[:500])
        
        # 有工具调用 - 粘贴 response 并提交
        print(f"[Turn {turn}] 提交 response（{len(response)} chars）...")
        paste_and_submit_via_ui(win, response)
        
        # 等待 REPL 处理（工具执行）
        print(f"[Turn {turn}] 等待工具执行...")
        time.sleep(8)
        
        # 检查新 prompt
        new_prompt = wait_for_prompt_file(io_dir, timeout=30)
        if new_prompt and new_prompt != current_prompt:
            current_prompt = new_prompt
            print(f"[Turn {turn}] 新 prompt 生成，继续")
        else:
            final = check_final_answer(io_dir)
            if final:
                print(f"[完成] 任务完成")
                return final
            else:
                print(f"[Turn {turn}] 无新 prompt，检查状态")
                break
    
    return None


# ============ 入口 ============

if __name__ == '__main__':
    task = "请计算 1+1 等于几，简单任务，用于测试 UI 自动化流程"
    
    print("=" * 60)
    print("MyAgent UI 自动化测试")
    print("=" * 60)
    
    result = run_ui_automation(task, max_turns=10)
    
    print("\n" + "=" * 60)
    print(f"结果: {result}")
    print("=" * 60)
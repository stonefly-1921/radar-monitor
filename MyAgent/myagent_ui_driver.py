"""
MyAgent UI 自动化驱动
通过 pywinauto 操作 MyAgent Tkinter 窗口，模拟人工操作流程。
"""
import sys, os, time, json, urllib.request, urllib.error

# ============ LLM 调用 ============

def call_llm(messages: list, model: str = "MiniMax-M2.7") -> str:
    api_key = os.environ.get("MINIMAX_API_KEY", "")
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


# ============ MyAgent UI 连接 ============

def get_myagent_window():
    """连接到 MyAgent v2.1 窗口。"""
    from pywinauto import Application
    app = Application(backend="win32").connect(process=18012)
    return app.window(title="MyAgent v2.1")


def find_controls(win):
    """打印所有控件的坐标和类型，方便调试。"""
    for c in win.children():
        try:
            r = c.rectangle()
            print(f'  [{c.class_name}] HWND={c.handle} L={r.left},T={r.top},R={r.right},B={r.bottom} text={repr(c.window_text()[:20])}')
        except Exception as e:
            print(f'  [{c.class_name}] err={e}')


# ============ 核心操作函数 ============

def input_task(win, task_text: str):
    """
    操作流程：
    1. 点击任务输入框（TkChild at L=80,T=172,R=858,B=282）
    2. 清空内容
    3. 输入任务文本
    """
    # 任务输入框
    task_input = None
    for c in win.children():
        try:
            r = c.rectangle()
            if r.left == 80 and r.top == 172 and r.right == 858 and r.bottom == 282:
                task_input = c
                break
        except:
            pass
    
    if task_input is None:
        print("[错误] 未找到任务输入框")
        return False
    
    print(f"[UI] 找到任务输入框 HWND={task_input.handle}")
    
    # 点击并输入
    task_input.click_input()
    time.sleep(0.2)
    
    # 全选清空
    import pywinauto.keyboard as kb
    kb.send_keys('^a')
    time.sleep(0.1)
    kb.send_keys('{DELETE}')
    time.sleep(0.1)
    
    # 输入任务（分段落）
    # Tkinter Text widget 用 typewrite 或者直接 set_edit_text
    try:
        task_input.set_edit_text(task_text)
        print("[UI] set_edit_text 成功")
        return True
    except Exception as e:
        print(f"[UI] set_edit_text 失败: {e}")
        # 备用：用 keyboard 输入
        kb.send_keys(task_text[:100])
        return True


def click_start_button(win):
    """点击'开始任务'按钮（HWND=265380，左面板下方）"""
    for c in win.children():
        try:
            r = c.rectangle()
            if r.left == 80 and r.top == 290 and r.right == 858 and r.bottom == 358:
                c.click_input()
                print(f"[UI] 已点击开始任务 HWND={c.handle}")
                return True
        except:
            pass
    print("[错误] 未找到开始任务按钮")
    return False


def wait_for_prompt(win, timeout=30):
    """等待 prompt 生成（轮询 io/prompt.txt）"""
    io_dir = os.path.join(os.path.dirname(__file__), "io")
    prompt_file = os.path.join(io_dir, "prompt.txt")
    
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(prompt_file):
            content = open(prompt_file, encoding='utf-8').read().strip()
            if content:
                print(f"[UI] prompt 生成完成，长度={len(content)}")
                return content
        time.sleep(1)
        print(f"[UI] 等待 prompt... ({int(time.time()-start)}s)")
    
    print("[错误] prompt 生成超时")
    return None


def read_prompt_from_ui(win):
    """从 UI 的 prompt 文本区读取内容（TkChild at L=886,T=168,R=2422,B=782）"""
    for c in win.children():
        try:
            r = c.rectangle()
            if r.left == 886 and r.top == 168 and r.right == 2422 and r.bottom == 782:
                text = c.window_text()
                print(f"[UI] 从 UI 读取 prompt，长度={len(text)}")
                return text
        except:
            pass
    print("[错误] 未找到 prompt 文本区")
    return None


def paste_response(win, response_text: str):
    """在 response 文本区输入回复（TkChild at L=886,T=900,R=2422,B=1516）"""
    for c in win.children():
        try:
            r = c.rectangle()
            if r.left == 886 and r.top == 900 and r.right == 2422 and r.bottom == 1516:
                c.click_input()
                time.sleep(0.1)
                try:
                    c.set_edit_text(response_text)
                    print(f"[UI] 已设置 response 内容，长度={len(response_text)}")
                except Exception as e:
                    print(f"[UI] set_edit_text 失败: {e}")
                    import pywinauto.keyboard as kb
                    kb.send_keys('^a')
                    kb.send_keys(response_text)
                return True
        except:
            pass
    print("[错误] 未找到 response 文本区")
    return False


def click_submit_button(win):
    """点击'粘贴&提交'按钮（HWND=15273062，右下区域）"""
    for c in win.children():
        try:
            r = c.rectangle()
            # 粘贴&提交 button at L=886, T=1522, R=2456, B=1582
            if r.left == 886 and r.top == 1522 and r.right == 2456 and r.bottom == 1582:
                c.click_input()
                print(f"[UI] 已点击粘贴&提交 HWND={c.handle}")
                return True
        except:
            pass
    print("[错误] 未找到提交按钮")
    return False


def check_final_answer():
    """检查 final_answer.txt 是否存在"""
    io_dir = os.path.join(os.path.dirname(__file__), "io")
    final_file = os.path.join(io_dir, "final_answer.txt")
    if os.path.exists(final_file):
        content = open(final_file, encoding='utf-8').read().strip()
        if content:
            return content
    return None


def get_execution_log(win):
    """读取执行过程日志区域（TkChild at L=80,T=424,R=824,B=1490）"""
    for c in win.children():
        try:
            r = c.rectangle()
            if r.left == 80 and r.top == 424 and r.right == 824 and r.bottom == 1490:
                text = c.window_text()
                return text[-2000:]  # 最近 2000 字符
        except:
            pass
    return ""


# ============ 主自动化流程 ============

def run_automation_loop(task: str, max_turns: int = 20):
    """自动执行多轮 REPL 循环。"""
    
    print("[UI] 连接 MyAgent 窗口...")
    win = get_myagent_window()
    print(f"[UI] 窗口已连接")
    
    # Step 1: 输入任务
    print("[UI] Step 1: 输入任务...")
    input_task(win, task)
    time.sleep(0.3)
    
    # Step 2: 点击开始任务
    print("[UI] Step 2: 点击开始任务...")
    click_start_button(win)
    
    # Step 3: 等待 prompt 生成
    print("[UI] Step 3: 等待 prompt 生成...")
    prompt = wait_for_prompt(win, timeout=30)
    if not prompt:
        print("[错误] 无法获取 prompt，退出")
        return
    
    # ========== 多轮循环 ==========
    turn = 0
    while turn < max_turns:
        turn += 1
        print(f"\n{'='*60}")
        print(f"[Turn {turn}] 将 prompt 发给 LLM...")
        
        # 调用 LLM
        messages = [{"role": "user", "content": prompt}]
        response = call_llm(messages)
        
        if response is None:
            print("[错误] LLM 调用失败")
            break
        
        print(f"[Turn {turn}] LLM 回复长度: {len(response)}")
        
        # 检查是否是 final answer
        parsed = parse_response(response)
        if parsed.get("action") == "final":
            print(f"[Turn {turn}] LLM 返回最终答案")
            final_content = parsed.get("content", response)
            
            # 粘贴到 response 区并提交
            paste_response(win, response)
            time.sleep(0.3)
            click_submit_button(win)
            time.sleep(2)
            
            # 检查最终答案
            final = check_final_answer()
            if final:
                print(f"[完成] 任务完成！最终答案长度: {len(final)}")
                return final
            else:
                print(f"[完成] LLM 直接给出答案:\n{final_content[:500]}")
                return final_content
        
        # 不是最终答案：粘贴 response 并提交
        print(f"[Turn {turn}] 粘贴 response 并提交...")
        paste_response(win, response)
        time.sleep(0.3)
        click_submit_button(win)
        
        # 等待工具执行
        print(f"[Turn {turn}] 等待工具执行...")
        time.sleep(5)
        
        # 检查是否有新 prompt（REPL 处理完后会写新 prompt）
        new_prompt = wait_for_new_prompt(win)
        if new_prompt and new_prompt != prompt:
            prompt = new_prompt
            print(f"[Turn {turn}] 新 prompt 生成，继续...")
        else:
            # 检查是否完成
            final = check_final_answer()
            if final:
                print(f"[完成] 任务完成！")
                return final
            else:
                print(f"[Turn {turn}] 未生成新 prompt，检查执行日志")
                log = get_execution_log(win)
                print(f"[Log] {log[-500:]}")
                break
    
    return None


def parse_response(raw: str) -> dict:
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
            return {"action": "tool_call", "tool_calls": data['tools'], "content": data.get('think', '')}
        elif data['action'] == 'final':
            return {"action": "final", "content": data.get('answer', ''), "tool_calls": []}
    if 'tool_calls' in data and data['tool_calls']:
        return {"action": "tool_call", "tool_calls": data['tool_calls'], "content": data.get('content', '')}
    return {"action": "final", "content": raw, "tool_calls": []}


def wait_for_new_prompt(win, timeout=30):
    """等待新的 prompt 生成。"""
    io_dir = os.path.join(os.path.dirname(__file__), "io")
    prompt_file = os.path.join(io_dir, "prompt.txt")
    
    # 记录当前 prompt 内容
    current = ""
    if os.path.exists(prompt_file):
        current = open(prompt_file, encoding='utf-8').read().strip()
    
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(2)
        if os.path.exists(prompt_file):
            content = open(prompt_file, encoding='utf-8').read().strip()
            if content and content != current:
                print(f"[UI] 新 prompt 生成，长度={len(content)}")
                return content
        print(f"[UI] 等待新 prompt... ({int(time.time()-start)}s)")
    
    return None


# ============ 入口 ============

if __name__ == '__main__':
    task = """请找本机的 AFSIM 2.9.0 仿真源码，然后去读相关关于弹道导弹仿真的部分，并做一个弹道，从北京到台北。

步骤：
1. 列出目录 D:\\afsim-2.9.0-win64\\swdev\\src\\wsf_plugins\\wsf_fires\\source\\ 的文件
2. 读 FiresPath.cpp 理解弹道模型（一阶阻力模型）
3. 用 python_run 计算从北京(39.9°N, 116.4°E)到台北(25.0°N, 121.5°E)的弹道
4. 输出完整结果

AFSIM 源码在此：D:\\afsim-2.9.0-win64\\swdev\\src\\wsf_plugins\\wsf_fires\\source\\"""
    
    print("=" * 60)
    print("MyAgent UI 自动化驱动")
    print("=" * 60)
    
    # 先诊断 UI 控件
    print("\n[诊断] 列出所有控件:")
    win = get_myagent_window()
    find_controls(win)
    
    print("\n[开始] 执行自动化任务...")
    result = run_automation_loop(task, max_turns=20)
    
    print("\n" + "=" * 60)
    print(f"结果: {result[:500] if result else 'None'}")
    print("=" * 60)
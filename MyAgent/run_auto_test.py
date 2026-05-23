"""
Auto Test Runner for MyAgent - 全自动串联千问桌面版
测试三个任务并统计模型调用次数

Workflow:
1. 写任务到 io/input.txt
2. MyAgent 生成 prompt.txt
3. send_to_qianwen.py 自动粘帖到千问窗口
4. 等待用户/自动读取千问回复
5. 粘帖到 io/response.txt
6. MyAgent 解析并执行工具
7. 多轮循环直到 final answer
8. 统计工具调用次数

环境: Win7 隔离网，不改变任何依赖
"""

import os
import sys
import time
import json
import pyautogui
import win32gui
import pyperclip
import subprocess

# Add project root to path
sys.path.insert(0, 'C:/Users/15041/.openclaw/workspace/MyAgent')

# Qwen window handle
HWND_QIANWEN = 1575860

# IO paths
BASE_DIR = 'C:/Users/15041/.openclaw/workspace/MyAgent'
INPUT_FILE = os.path.join(BASE_DIR, 'io', 'input.txt')
PROMPT_FILE = os.path.join(BASE_DIR, 'io', 'prompt.txt')
RESPONSE_FILE = os.path.join(BASE_DIR, 'io', 'response.txt')
TOOL_RESULT_FILE = os.path.join(BASE_DIR, 'io', 'tool_result.json')

# Call tracking
model_call_count = 0
tool_call_count = 0


def read_file(path):
    """Read text file"""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def write_file(path, content):
    """Write text file"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def focus_qianwen():
    """Focus Qwen window"""
    win32gui.SetForegroundWindow(HWND_QIANWEN)
    time.sleep(0.3)


def send_to_qianwen(prompt_text):
    """Paste prompt to Qwen window and send"""
    focus_qianwen()
    
    # Click input area
    pyautogui.click(x=1434, y=1500)
    time.sleep(0.3)
    
    # Clear and paste
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.1)
    pyautogui.press('delete')
    time.sleep(0.2)
    
    pyperclip.copy(prompt_text)
    time.sleep(0.1)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.5)
    
    # Send
    pyautogui.press('enter')
    print(f"[SEND] Prompt sent ({len(prompt_text)} chars)")


def wait_for_response(timeout=60, poll_interval=3):
    """Wait for Qwen response by polling clipboard changes"""
    print(f"[WAIT] Waiting for Qwen response (timeout={timeout}s)...")
    start = time.time()
    last_len = 0
    
    while time.time() - start < timeout:
        time.sleep(poll_interval)
        
        # Check clipboard periodically
        try:
            clip = pyperclip.paste()
            if len(clip) > last_len and '。' in clip[-50:] or 'answer' in clip.lower() or 'result' in clip.lower():
                print(f"[WAIT] Response detected ({len(clip)} chars), waiting more for completion...")
                time.sleep(5)  # Extra wait for Qwen to finish streaming
                last_len = len(clip)
        except:
            pass
        
        # Check if response file has been updated (user manual paste alternative)
        if os.path.exists(RESPONSE_FILE):
            content = read_file(RESPONSE_FILE).strip()
            if content and len(content) > 100:
                return content
    
    print("[WAIT] Timeout waiting for response")
    return None


def read_qwen_response():
    """Read response from Qwen window via UI automation"""
    focus_qianwen()
    time.sleep(0.5)
    
    # Try to select all and copy from message area
    # Click at different positions to find the response
    positions = [(1434, 500), (1434, 700), (1434, 900)]
    best_response = ""
    
    for x, y in positions:
        pyautogui.click(x=x, y=y)
        time.sleep(0.2)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.2)
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(0.3)
        clip = pyperclip.paste()
        
        if len(clip) > len(best_response) and ('answer' in clip.lower() or 'result' in clip.lower() or '总结' in clip or '回答' in clip):
            best_response = clip
    
    return best_response if best_response else None


def write_input(task):
    """Write user task to input.txt"""
    write_file(INPUT_FILE, task)
    print(f"[INPUT] Task written: {task[:50]}...")


def get_response_from_qwen():
    """Get Qwen response - check response.txt first (manual paste fallback), then UI"""
    # Check if response.txt has content (manual paste method)
    if os.path.exists(RESPONSE_FILE):
        content = read_file(RESPONSE_FILE).strip()
        if content and len(content) > 50:
            return content
    
    # Try UI reading
    return read_qwen_response()


def parse_response_and_execute(response_text, loop):
    """Parse LLM response and execute tools"""
    global tool_call_count
    
    result = loop.parse_response(response_text)
    
    if not result.get('content') and not result.get('tool_calls'):
        return None, "failed", "Empty response"
    
    action = result.get('action', 'final')
    content = result.get('content', '')
    tool_calls = result.get('tool_calls', [])
    
    if action == 'final':
        return content, 'final', None
    
    if action == 'tool_call':
        results = []
        for tc in tool_calls:
            tool_name = tc.get('tool') or tc.get('name', 'unknown')
            params = tc.get('params') or tc.get('arguments', {})
            
            print(f"[TOOL CALL {tool_call_count+1}] {tool_name}: {params}")
            
            res = loop.registry.execute(tool_name, **params)
            tool_call_count += 1
            results.append({
                "tool": tool_name,
                "params": params,
                "result": res
            })
            
            print(f"[TOOL RESULT] {tool_name}: {'OK' if res.get('success') else 'FAIL'}")
        
        return results, 'tool_calls', None
    
    return content, action, None


def run_task(task, max_turns=10):
    """Run a single task through MyAgent + Qwen"""
    global model_call_count
    
    print("\n" + "="*60)
    print(f"TASK: {task[:60]}...")
    print("="*60)
    
    # Initialize loop
    from agent.loop_v2 import AgentLoopV2
    loop = AgentLoopV2()
    loop.initialize()
    
    write_input(task)
    
    for turn in range(1, max_turns + 1):
        print(f"\n--- Turn {turn} ---")
        
        # Build prompt
        conversation = loop.session.get_conversation_history() if loop.session else []
        prompt = loop.build_prompt_text(task, turn=turn, tool_results=None, conversation=conversation)
        
        write_file(PROMPT_FILE, prompt)
        print(f"[PROMPT] Generated ({len(prompt)} chars)")
        
        # Send to Qwen
        send_to_qianwen(prompt)
        model_call_count += 1
        
        # Wait for response
        response = wait_for_response(timeout=120)
        
        if not response:
            print("[ERROR] No response from Qwen")
            break
        
        # Write to response.txt for loop to parse
        write_file(RESPONSE_FILE, response)
        print(f"[RESPONSE] Received ({len(response)} chars)")
        
        # Parse and execute
        result, action, err = parse_response_and_execute(response, loop)
        
        if action == 'final':
            print(f"\n✅ FINAL ANSWER: {str(result)[:200]}...")
            return result, turn
        
        if action == 'tool_calls':
            # Continue loop - save tool results and regenerate prompt
            tool_text = json.dumps(result, ensure_ascii=False, indent=2)
            # Note: in real REPL, loop handles this. Here we just continue.
            print(f"[CONTINUE] Executed {len(result)} tool calls, continuing...")
            continue
    
    return None, max_turns


def main():
    print("="*60)
    print("  MyAgent Auto Test Runner")
    print("  Win7 隔离网环境测试")
    print("="*60)
    
    tasks = [
        {
            "id": 1,
            "name": "文件查找与理解",
            "task": "请在 C:\\Users\\15041\\.openclaw\\workspace\\MyAgent 目录下找一个 Python 文件，读取它的内容，理解并总结其中的主要功能。"
        },
        {
            "id": 2,
            "name": "PDF分析生成综述",
            "task": "请读取桌面上所有PDF文件（论文和论文2文件夹中的），分析其中的内容，生成一个综述性的文献报告，保存为Word文档。"
        },
        {
            "id": 3,
            "name": "代码调试",
            "task": "请用Python写一个大于1000行的简单程序（可以是学生成绩管理系统），包含一些常见的bug，然后调试它使其正常运行。"
        }
    ]
    
    results = []
    
    for td in tasks:
        try:
            result, turns = run_task(td['task'])
            results.append({
                "id": td['id'],
                "name": td['name'],
                "success": result is not None,
                "turns": turns,
                "model_calls": model_call_count,  # cumulative
                "tool_calls": tool_call_count     # cumulative
            })
        except Exception as e:
            print(f"[ERROR] Task {td['id']} failed: {e}")
            results.append({
                "id": td['id'],
                "name": td['name'],
                "success": False,
                "error": str(e)
            })
    
    # Summary
    print("\n" + "="*60)
    print("  Test Summary")
    print("="*60)
    
    for r in results:
        if r.get('success'):
            print(f"✅ Task {r['id']}: {r['name']} - {r['turns']} turns, {r['model_calls']} model calls, {r['tool_calls']} tool calls")
        else:
            print(f"❌ Task {r['id']}: {r['name']} - FAILED: {r.get('error', 'unknown')}")
    
    print("="*60)
    
    return results


if __name__ == "__main__":
    main()
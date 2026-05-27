"""
MyAgent CLI 模式
================
无需打开 UI，直接通过命令行测试 REPL 流程。

用法:
  python agent/cli.py                    # 交互模式
  python agent/cli.py "请计算1+1"        # 单次任务模式
  python agent/cli.py --once             # 读取 prompt.txt → 调用 LLM → 写入 response.txt
  python agent/cli.py --exec             # 完整多轮循环：input→prompt→LLM→工具→prompt→...→final
"""
import sys, os, time, json, subprocess

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent.persona import Persona
from agent.config import AgentConfig
from memory.core import Memory
from session import Session
from tools import get_initialized_registry
from agent.loop_v2 import AgentLoopV2, parse_response


# ===== API 配置 =====
API_KEY = subprocess.run(
    ['powershell', '-Command', "[Environment]::GetEnvironmentVariable('MINIMAX_API_KEY', 'User')"],
    capture_output=True, text=True, encoding='utf-8'
).stdout.strip()
ENDPOINT = "https://api.minimaxi.com/anthropic/v1/messages"
MODEL = "MiniMax-M2.7"


# ===== 路径 =====
MYAGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IO_DIR = os.path.join(MYAGENT_DIR, 'io')
os.makedirs(IO_DIR, exist_ok=True)


def get_api_key():
    return API_KEY


def call_llm(prompt_text: str) -> dict:
    """调用 LLM"""
    import urllib.request
    
    headers = {
        "Authorization": f"Bearer {get_api_key()}",
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt_text}],
        "max_tokens": 8192,
        "temperature": 0.7
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=data, headers=headers, method="POST")
    
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        for item in result.get("content", []):
            if item.get("type") == "text":
                text = item.get("text", "").strip()
                if text:
                    try:
                        return json.loads(text)
                    except:
                        return {"action": "final", "answer": text}
    return None


def read_file(path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return open(path, encoding="utf-8").read().strip()
    return ""


def write_file(path, content):
    open(path, "w", encoding="utf-8").write(content)


def run_once():
    """
    单次执行模式：
    读取 io/prompt.txt → 调用 LLM → 写入 io/response.txt
    """
    prompt_file = os.path.join(IO_DIR, "prompt.txt")
    response_file = os.path.join(IO_DIR, "response.txt")
    final_file = os.path.join(IO_DIR, "final_answer.txt")
    
    print("=" * 60)
    print("MyAgent CLI - 单次执行模式")
    print("=" * 60)
    
    # 读取 prompt.txt
    prompt = read_file(prompt_file)
    if not prompt:
        print("[错误] prompt.txt 为空，请先通过 UI 生成 prompt")
        return
    
    print(f"[读取] prompt.txt ({len(prompt)} chars)")
    
    # 调用 LLM
    print("[调用] LLM...")
    result = call_llm(prompt)
    
    if not result:
        print("[错误] LLM 调用失败")
        return
    
    print(f"[LLM] action={result.get('action', '?')}")
    
    # 写入 response.txt
    response_json = json.dumps(result, ensure_ascii=False)
    write_file(response_file, response_json)
    print(f"[写入] response.txt ({len(response_json)} chars)")
    
    # 如果是 final action，写入 final_answer.txt
    if result.get("action") == "final":
        answer = result.get("answer", "")
        write_file(final_file, answer)
        print(f"[完成] final_answer: {answer[:100]}")
    
    print("=" * 60)
    print("完成。现在可以启动 MyAgent UI 并点击「粘贴&提交」继续。")
    print("=" * 60)


def run_exec():
    """
    完整多轮执行模式（E2E测试核心）：
    1. 读取 io/input.txt 的任务
    2. 调用 AgentLoopV2._execute_task() 处理（内部生成 prompt.txt）
    3. 轮询等待 response.txt（测试方写入 LLM 回复）
    4. 解析 response，执行工具，继续循环
    5. 直到 final_answer 或达到最大轮次

    整个流程由 CLI 自己驱动，不需要 GUI。
    与 AgentLoopV2._testing_mode 等效，但通过文件驱动。
    """
    print("=" * 60)
    print("MyAgent CLI - 完整多轮执行模式 (--exec)")
    print("=" * 60)

    # 读取任务
    input_file = os.path.join(IO_DIR, "input.txt")
    response_file = os.path.join(IO_DIR, "response.txt")
    prompt_file = os.path.join(IO_DIR, "prompt.txt")
    final_file = os.path.join(IO_DIR, "final_answer.txt")

    task = read_file(input_file)
    if not task:
        print("[错误] input.txt 为空，请先写入任务")
        return

    print(f"[任务] {task[:80]}...")
    print("[说明] 等待 response.txt（LLM回复），按回车继续...\n")

    # 初始化 AgentLoopV2（不走 initialize()，直接用 _execute_task）
    # 因为 initialize() 会清空 io/ 文件，我们通过 input.txt 注入任务
    sys.path.insert(0, MYAGENT_DIR)
    from agent.loop_v2 import AgentLoopV2

    loop = AgentLoopV2()
    loop.base_dir = MYAGENT_DIR

    # 加载 session 和 memory（不调用 initialize()，避免清空 io 文件）
    session_file = os.path.join(IO_DIR, "session.json")
    loop.session = Session.load_or_create(session_file)
    loop.memory = Memory()

    # 初始化 registry 和 persona
    loop.registry = get_initialized_registry()
    loop.persona = Persona()
    loop.config = AgentConfig()

    # 重置 io/ 保留文件，但不删 prompt/response（需要它们做文件轮询）
    for fname in ["input.txt", "final_answer.txt"]:
        p = os.path.join(IO_DIR, fname)
        open(p, "w", encoding="utf-8").write("")

    # 执行任务主循环（模拟 _execute_task 的流程，但通过文件轮询获取 response）
    turn = 1
    tool_results = None
    user_input = task

    # 初始化 TaskState
    loop._init_task_state(user_input)

    # 保存用户输入到 session
    loop.session.add_turn({"input": user_input})

    max_turns = 8

    while turn <= max_turns:
        # === 生成 prompt.txt ===
        conversation = loop.session.get_conversation_history()
        prompt_text = loop.build_prompt_text(
            user_input=user_input,
            turn=turn,
            tool_results=tool_results,
            conversation=conversation
        )
        loop._save_prompt(prompt_text)
        print(f"[Turn {turn}] prompt.txt 已写入 ({len(prompt_text)} chars)")

        # === 等待 response.txt（轮询，模拟人类粘贴 LLM 回复）===
        print("[等待] 请把 LLM 回复粘贴到 response.txt...")
        response_text = _wait_for_response_file(response_file)
        if response_text is None:
            print("[取消] response.txt 未找到，任务取消")
            return

        # === 解析 response ===
        parsed = parse_response(response_text)
        print(f"[Turn {turn}] 解析结果: action={parsed['action']}")

        if parsed["action"] == "tool_call":
            tool_calls = parsed.get("tool_calls", [])
            if not tool_calls:
                # LLM 声明 tool_call 但 tool_calls 为空，跳过执行，进入下一轮
                print(f"[Turn {turn}] ⚠️ LLM 声明 tool_call 但 tool_calls 为空，跳过执行")
                results = []
            else:
                # === 执行工具 ===
                print(f"[Turn {turn}] 执行 {len(tool_calls)} 个工具...")
                results = loop._execute_tools_display(tool_calls)

            # 保存工具结果到 session
            turn_data = loop.session.get_last_turn()
            if turn_data:
                existing = turn_data.get("tool_calls", [])
                existing.extend(tool_calls)
                turn_data["tool_calls"] = existing
                existing_res = turn_data.get("tool_results", [])
                existing_res.extend(results)
                turn_data["tool_results"] = existing_res
            loop.session.save()

            # 更新 TaskState
            for tr in results:
                tool_name = tr.get('tool', 'unknown')
                res = tr.get('result', {})
                if res.get('success'):
                    finding = str(res.get('result', res.get('output', '')))[:80]
                else:
                    finding = f"FAIL: {res.get('error', 'unknown')}"
                loop._update_task_state(tr, finding)

            # 下一轮
            tool_results = results
            turn += 1
            if loop._task_state:
                loop._task_state["turn"] = turn
            print()
            continue

        else:
            # === 最终答案 ===
            final_content = parsed.get("content", "")
            print(f"\n[完成] 任务完成")
            print("=" * 60)
            print(f"最终答案:\n{final_content[:200]}")
            print("=" * 60)

            # 保存最终答案
            turn_data = loop.session.get_last_turn()
            if turn_data:
                turn_data["final_answer"] = final_content
            loop.session.save()

            # 写入 final_answer.txt
            write_file(final_file, final_content)
            return

    print(f"[警告] 达到最大轮次 {max_turns}，任务强制结束")


def _wait_for_response_file(response_file: str, timeout: int = 300) -> str:
    """
    轮询等待 response.txt 出现内容。
    每秒检查一次，超时返回 None。
    """
    import time as time_module
    start = time_module.time()
    interval = 1.0

    while time_module.time() - start < timeout:
        if os.path.exists(response_file):
            content = read_file(response_file)
            if content:
                # 清空文件（防止重复使用）
                open(response_file, "w", encoding="utf-8").write("")
                return content
        time_module.sleep(interval)

    return None


def interactive_mode():
    """
    交互模式：
    直接读取 input.txt，生成 prompt.txt，等待 response.txt，再次调用 LLM...
    """
    print("=" * 60)
    print("MyAgent CLI - 交互模式")
    print("=" * 60)
    print("读取 io/input.txt 的任务，按回车继续...")
    
    while True:
        print()
        task = input("任务 (输入 quit 退出): ").strip()
        if task.lower() == "quit":
            break
        
        # 写任务到 input.txt
        input_file = os.path.join(IO_DIR, "input.txt")
        write_file(input_file, task)
        print(f"[写入] input.txt: {task[:50]}...")
        
        # 等待用户按回车（表示 prompt.txt 已生成）
        input("按回车继续 (prompt.txt 已就绪)...")
        
        # 读取 prompt.txt
        prompt_file = os.path.join(IO_DIR, "prompt.txt")
        prompt = read_file(prompt_file)
        if not prompt:
            print("[错误] prompt.txt 为空")
            continue
        
        print(f"[读取] prompt.txt ({len(prompt)} chars)")
        
        # 调用 LLM
        print("[调用] LLM...")
        result = call_llm(prompt)
        if not result:
            print("[错误] LLM 调用失败")
            continue
        
        print(f"[LLM] action={result.get('action', '?')}")
        
        # 写入 response.txt
        response_json = json.dumps(result, ensure_ascii=False)
        response_file = os.path.join(IO_DIR, "response.txt")
        write_file(response_file, response_json)
        print(f"[写入] response.txt ({len(response_json)} chars)")
        
        # 如果是 final action
        if result.get("action") == "final":
            final_file = os.path.join(IO_DIR, "final_answer.txt")
            answer = result.get("answer", "")
            write_file(final_file, answer)
            print(f"[完成] final_answer: {answer[:100]}")
        
        # 等待用户按回车（表示已提交并获得新 prompt）
        input("按回车继续 (下一轮 prompt.txt 已就绪)...")


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--once":
            run_once()
        elif sys.argv[1] == "--exec":
            run_exec()
        elif sys.argv[1] == "--help":
            print(__doc__)
        else:
            # 单次任务模式
            task = sys.argv[1]
            input_file = os.path.join(IO_DIR, "input.txt")
            write_file(input_file, task)
            print(f"[任务] {task}")
            print("[提示] 请手动触发 REPL 处理，或使用 --once 模式")
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
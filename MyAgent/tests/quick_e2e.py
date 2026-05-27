"""
快速E2E验证脚本 - 直接实例化AgentLoopV2
不依赖cli.py subprocess，用真实LLM API做端到端测试
"""
import os
import sys
import json
import subprocess
import urllib.request

# === 配置 ===
MYAGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, MYAGENT_DIR)

def get_api_key():
    result = subprocess.run(
        ["powershell", "-Command", "[Environment]::GetEnvironmentVariable('MINIMAX_API_KEY', 'User')"],
        capture_output=True, text=True, encoding="utf-8"
    )
    return result.stdout.strip()

API_KEY = get_api_key()
LLM_ENDPOINT = "https://api.minimaxi.com/anthropic/v1/messages"
LLM_MODEL = "MiniMax-M2.7"
def call_llm(prompt_text: str) -> dict:
    """直接调用 LLM API，返回 parsed JSON"""
    import urllib.request
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt_text}],
        "max_tokens": 8192,
        "temperature": 0.3
    }
    req = urllib.request.Request(
        LLM_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        for item in result.get("content", []):
            if item.get("type") == "text":
                text = item.get("text", "").strip()
                if text:
                    try:
                        parsed = json.loads(text)
                        # 确保返回的是 dict，不是 int/str 等
                        if isinstance(parsed, dict):
                            return parsed
                        # LLM 返回了纯数字/纯文本，当作 final
                        return {"action": "final", "answer": str(parsed)}
                    except json.JSONDecodeError:
                        return {"action": "final", "answer": text}
    return None

def run_test(task: str, expected_contains: str = None, max_turns: int = 6):
    """运行单个E2E测试"""
    from agent.loop_v2 import AgentLoopV2
    from memory.core import Memory
    from agent.persona import Persona
    from agent.config import AgentConfig
    from tools import get_initialized_registry

    print(f"\n{'='*60}")
    print(f"任务: {task[:80]}...")
    print(f"{'='*60}")

    from session import Session

    # 初始化
    loop = AgentLoopV2()
    loop.base_dir = MYAGENT_DIR
    loop.registry = get_initialized_registry()
    loop.persona = Persona()
    loop.config = AgentConfig()
    loop.memory = Memory()
    loop.session = Session.load_or_create(os.path.join(MYAGENT_DIR, "io", "session.json"))
    loop._init_task_state(task)
    loop.session.add_turn({"input": task})

    # 手动轮询控制 - 直接用真实LLM
    turn = 1
    tool_results = None

    while turn <= max_turns:
        # 生成prompt
        conversation = loop.session.get_conversation_history()
        prompt_text = loop.build_prompt_text(
            user_input=task,
            turn=turn,
            tool_results=tool_results,
            conversation=conversation
        )

        # 调用LLM
        print(f"[Turn {turn}] 调用LLM...")
        resp = call_llm(prompt_text)
        if not resp:
            print(f"[错误] LLM调用失败")
            return False

        action = resp.get("action", "?")
        print(f"[Turn {turn}] action={action}")

        if action == "tool_call":
            tool_calls = resp.get("tool_calls", [])
            print(f"[Turn {turn}] 执行 {len(tool_calls)} 个工具调用...")
            for tc in tool_calls:
                print(f"  -> {tc.get('tool', '?')}: {str(tc.get('params', {}))[:60]}")

            if not tool_calls:
                # LLM 声明 tool_call 但没有 tools 数组
                # 检查是否有其他工具信息
                tools_key = resp.get("tools", [])
                if tools_key:
                    tool_calls = tools_key
                else:
                    # 视为 final，用 think 内容作为答案
                    print(f"[警告] action=tool_call 但 tools 为空，视为 final")
                    answer = resp.get("think", resp.get("answer", ""))
                    print(f"[完成] 答案: {str(answer)[:100]}")
                    if expected_contains:
                        ok = expected_contains in str(answer)
                        print(f"[{'PASS' if ok else 'FAIL'}] 期望 '{expected_contains}' 在答案中")
                        return ok
                    return True

            results = loop._execute_tools_display(tool_calls)
            for r in results:
                name = r.get('tool', '?')
                ok = r.get('result', {}).get('success', False)
                print(f"  <- {name}: {'OK' if ok else 'FAIL'} {str(r.get('result', {}).get('result', ''))[:60]}")

            tool_results = results

            turn_data = loop.session.get_last_turn()
            if turn_data:
                turn_data['tool_calls'] = turn_data.get('tool_calls', []) + tool_calls
                turn_data['tool_results'] = turn_data.get('tool_results', []) + results

            turn += 1
            continue

        elif action == "final":
            answer = resp.get("answer", "")
            print(f"[完成] 答案: {str(answer)[:100]}")
            if expected_contains:
                if expected_contains in str(answer):
                    print(f"[PASS] 包含期望内容: {expected_contains}")
                    return True
                else:
                    print(f"[FAIL] 期望 '{expected_contains}' 但得到 '{str(answer)[:50]}'")
                    return False
            return True

        else:
            # 未知action，记录并继续
            print(f"[警告] 未知action: {action}, resp={str(resp)[:100]}")
            turn += 1
            continue

    print(f"[超时] 达到最大轮次 {max_turns}")
    return False

# =============================================================================
# 测试用例
# =============================================================================

if __name__ == "__main__":
    tests = [
        # 基础工具调用
        ("计算1+1", "请用python_run工具计算1+1等于几，结果直接输出", "2"),
        ("计算2*3", "用python_run工具计算2乘以3等于几", "6"),
        ("计算阶乘", "用python_run计算5的阶乘", "120"),
        ("列出py文件", "用file_list工具列出当前目录下所有.py文件（不含子目录），输出前3个", ".py"),

        # 多轮工具调用
        ("先列后读", "用file_list列出当前目录的.py文件，然后读第一个文件的内容", "import"),

        # 错误处理
        ("错误路径", "用file_read读取一个肯定不存在的文件/nonexistent_file_xyz.txt，告诉我错误信息", "不存在"),

        # Session/History
        ("第二次同类任务", "再次计算1+1等于几（第二次问）", "2"),

        # Shell工具
        ("shell运行", "用shell_run工具执行命令: echo hello world", "hello"),
        ("shell列出目录", "用shell_run执行: dir *.py /b", ".py"),

        # Python多行脚本
        ("Python多行", "用python_run工具执行: x=[1,2,3]; print(sum(x))", "6"),
        ("Python条件", "用python_run执行if判断: print('big' if 100>50 else 'small')", "big"),

        # Grep工具
        ("grep搜索", "用grep工具在当前目录搜索包含'AgentLoop'的.py文件", "AgentLoop"),
        ("grep多结果", "用grep搜索当前目录含'def '的.py文件", "def"),

        # FileWrite工具
        ("写文件", "用file_write工具写入内容'hello world'到io/test_write.txt，然后读回来验证", "hello"),

        # 工具组合
        ("工具链", "1.用shell_run执行: echo test > io/test_chain.txt 2.用file_read读取io/test_chain.txt", "test"),

        # 计算类
        ("数学计算", "用python_run计算: 2**10等于多少", "1024"),
        ("字符串处理", "用python_run计算: len('hello world')", "11"),

        # 错误恢复
        ("错误后重试", "读取一个不存在的文件io/notexist.txt，然后读取io/input.txt验证", "不存在"),
    ]

    passed = 0
    failed = 0

    for name, task, expected in tests:
        try:
            ok = run_test(task, expected_contains=expected, max_turns=8)
            if ok:
                passed += 1
                print(f"[结果] {name}: PASS")
            else:
                failed += 1
                print(f"[结果] {name}: FAIL")
        except Exception as e:
            failed += 1
            print(f"[结果] {name}: ERROR - {e}")
            import traceback; traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"测试完成: {passed} passed, {failed} failed")
    print(f"{'='*60}")
"""
MyAgent 自动化测试脚本 - 让 MyAgent 真正跑起来
用法: python test_myagent_auto.py
"""
import sys, os, json, time
sys.path.insert(0, r'C:\Users\15041\.openclaw\workspace\MyAgent')

from agent import loop_v2
from tools import get_initialized_registry

# ============ LLM 调用（直接用 HTTP，不走文件 REPL）===========
LLM_API_URL = "https://api.minimax.chat/v1/text/chatcompletion_v2"
LLM_API_KEY = os.environ.get("MINIMAX_API_KEY", "")

def call_llm(messages: list, model: str = "MiniMax-M2.7") -> str:
    """直接调用 LLM API 返回文本。"""
    if not LLM_API_KEY:
        # fallback: 读文件模拟 LLM（仅测试用）
        return None
    
    import urllib.request, urllib.error
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 8192,
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        LLM_API_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[LLM ERROR] {e}")
        return None


# ============ 任务执行器（核心：让 MyAgent 自主跑多轮）===========

def execute_task_autonomously(task: str, max_turns: int = 20):
    """
    让 MyAgent 自主执行任务，不依赖人工粘贴。
    
    流程：生成 prompt → 调用 LLM → 解析 tool_calls → 执行工具 → 重复
    """
    registry = get_initialized_registry()
    
    # 初始化 session 和 persona
    persona_prompt = """你是一个专业的代码助手，功能是：
1. 读取和分析源代码文件
2. 执行 Python 脚本进行计算
3. 总结分析结果

你的工具：
- file_list: 列出目录下的文件
- file_read: 读取文件内容
- python_run: 执行 Python 脚本

输出格式（严格 JSON）：
{"think": "...", "action": "tool_call", "tools": [{"tool": "工具名", "params": {"参数": "值"}}]}
{"think": "...", "action": "final", "answer": "..."}

Windows 路径在 JSON 中必须双反斜杠转义：
C:\\Users\\15041\\Desktop
"""

    conversation = [{"role": "system", "content": persona_prompt}]
    user_input = task
    tool_results = None
    turn = 0

    while turn < max_turns:
        turn += 1
        print(f"\n{'='*60}")
        print(f"[Turn {turn}] 生成 prompt...")

        # 构建 prompt（模拟 loop_v2.build_prompt_text 的核心逻辑）
        prompt_parts = [persona_prompt, f"\n【当前任务】\n{task}\n"]
        
        if tool_results:
            prompt_parts.append("\n【上次工具结果】\n")
            for tr in tool_results:
                name = tr.get('tool', '?')
                ok = tr.get('result', {}).get('success', False)
                if ok:
                    res = str(tr.get('result', {}).get('result', ''))[:300]
                    prompt_parts.append(f"  {name} OK: {res}\n")
                else:
                    err = tr.get('result', {}).get('error', '?')
                    prompt_parts.append(f"  {name} FAIL: {err}\n")

        prompt_parts.append("\n【输出格式】严格 JSON: {\"think\": \"...\", \"action\": \"tool_call\" / \"final\", ...}\n")

        messages = conversation + [{"role": "user", "content": "".join(prompt_parts)}]

        # 调用 LLM
        print(f"[Turn {turn}] 调用 LLM...")
        response = call_llm(messages)
        if response is None:
            print("[LLM] API 密钥未配置或调用失败，退出")
            break

        print(f"[Turn {turn}] LLM 回复已收到 ({len(response)} chars)")

        # 解析 response
        parsed = parse_response(response)
        
        if parsed["action"] != "tool_call":
            # 最终答案
            print(f"\n[完成] 共 {turn} 轮，任务完成")
            return {"success": True, "content": parsed.get("content", ""), "turns": turn}

        # 执行工具
        tool_calls = parsed.get("tool_calls", [])
        print(f"[Turn {turn}] 执行 {len(tool_calls)} 个工具...")

        results = []
        for tc in tool_calls:
            tool_name = tc.get("tool")
            params = tc.get("params", {})
            print(f"  → {tool_name}: {str(params)[:60]}")
            
            res = registry.execute(tool_name, **params)
            results.append({"tool": tool_name, "params": params, "result": res})
            
            ok = res.get("success", False)
            print(f"    {'OK' if ok else 'FAIL'}: {res.get('result', res.get('error', ''))[:100]}")

        tool_results = results
        conversation.append({"role": "user", "content": f"工具结果: {json.dumps(results, ensure_ascii=False)[:500]}"})
        conversation.append({"role": "assistant", "content": response})

    print(f"\n[超时] 达到最大轮次 {max_turns}")
    return {"success": False, "error": "max turns exceeded", "turns": turn}


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
        action = data['action']
        if action == 'tool_call' and 'tools' in data:
            return {"action": "tool_call", "tool_calls": data['tools'], "content": data.get('think', '')}
        elif action == 'final':
            return {"action": "final", "content": data.get('answer', ''), "tool_calls": []}

    if 'tool_calls' in data and data['tool_calls']:
        return {"action": "tool_call", "tool_calls": data['tool_calls'], "content": data.get('content', '')}

    return {"action": "final", "content": raw, "tool_calls": []}


# ============ 主测试入口 ============

if __name__ == '__main__':
    USER_TASK = """请找本机的 AFSIM 2.9.0 仿真源码，然后去读相关关于弹道导弹仿真的部分，并做一个弹道，从北京到台北。

具体步骤：
1. 列出目录 D:\afsim-2.9.0-win64\swdev\src\wsf_plugins\wsf_fires\source\ 下的文件
2. 读 FiresPath.cpp 理解弹道计算（一阶阻力模型）
3. 用 Python 计算从北京(39.9°N, 116.4°E)到台北(25.0°N, 121.5°E)的弹道参数
4. 输出完整结果

AFSIM 源码在此：D:\afsim-2.9.0-win64\swdev\src\wsf_plugins\wsf_fires\source\
"""

    print("=" * 60)
    print("MyAgent 自动化测试")
    print("=" * 60)
    print(f"\n任务: {USER_TASK[:80]}...\n")

    start = time.time()
    result = execute_task_autonomously(USER_TASK, max_turns=20)
    elapsed = time.time() - start

    print("\n" + "=" * 60)
    print(f"结果: {'成功' if result.get('success') else '失败'}")
    print(f"耗时: {elapsed:.1f}s")
    print(f"轮次: {result.get('turns', '?')}")
    content = result.get('content', '')
    if content:
        print(f"答案:\n{content[:1000]}")
    print("=" * 60)
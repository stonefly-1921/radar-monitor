"""
MyAgent 自动化驱动 - 让 MyAgent 真正自主跑任务

核心思路：不走 REPL 文件模式，直接在 Python 里调用 LLM API，
模拟 loop_v2 的逻辑，自主执行多轮工具调用。

API 调用走 OpenClaw 的 minimax provider（通过环境变量）。
"""
import sys, os, json, time, urllib.request, urllib.error

# ============ LLM 调用 ============

def call_llm(messages: list, model: str = "MiniMax-M2.7") -> str:
    """调用 minimax LLM API。"""
    # 从 OpenClaw 配置获取 API key（通过环境变量或直接读文件）
    api_key = os.environ.get("MINIMAX_API_KEY", "")
    
    # 备用：从 OpenClaw 配置读
    if not api_key:
        config_path = r"C:\Users\15041\.openclaw\openclaw.json"
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                raw = f.read()
            # 找 apiKey 字段（redacted 格式）
            import re
            m = re.search(r'"apiKey":\s*"([^"]+)"', raw)
            if m:
                api_key = m.group(1)
        except:
            pass
    
    if not api_key:
        return None

    url = "https://api.minimaxi.com/anthropic/v1/messages"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 8192,
        "temperature": 0.7,
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result["content"][0]["text"]
    except Exception as e:
        print(f"[LLM ERROR] {e}")
        return None


# ============ 工具执行（走 MyAgent 的 registry） ============

def setup_tools():
    sys.path.insert(0, r'C:\Users\15041\.openclaw\workspace\MyAgent')
    from tools import get_initialized_registry
    return get_initialized_registry()


# ============ Prompt 构建（模拟 loop_v2 的 build_prompt_text） ============

def build_prompt(task, tool_results, turn):
    system = """你是一个专业的代码助手。你有以下工具可用：
- file_list(path): 列出目录下的文件
- file_read(path): 读取文件内容
- python_run(script): 执行 Python 代码（返回输出）

任务要求：
1. 先列出源码目录文件
2. 读 FiresPath.cpp 理解弹道计算（一阶阻力模型）
3. 用 python_run 执行弹道计算
4. 输出完整结果

输出格式（严格 JSON）：
{"think": "思考", "action": "tool_call", "tools": [{"tool": "工具名", "params": {"path"/"script": "值"}}]}
{"think": "思考", "action": "final", "answer": "最终答案"}

Windows 路径在 JSON 中用双反斜杠转义：D:\\\\afsim-2.9.0-win64\\\\swdev\\\\src\\\\..."""

    parts = [system, f"\n【任务】{task}\n"]
    
    if tool_results:
        parts.append("\n【工具结果】\n")
        for tr in tool_results:
            name = tr.get('tool', '?')
            ok = tr.get('result', {}).get('success', False)
            if ok:
                res = str(tr.get('result', {}).get('result', ''))[:500]
                parts.append(f"[{name}] OK: {res}\n")
            else:
                err = tr.get('result', {}).get('error', '?')
                parts.append(f"[{name}] FAIL: {err}\n")
    
    parts.append(f"\n【轮次】{turn}/20\n")
    parts.append('\n输出 JSON：')
    
    return "".join(parts)


def parse_response(raw: str) -> dict:
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


# ============ 主流程 ============

def run_task(task: str):
    registry = setup_tools()
    
    print("=" * 60)
    print("MyAgent 自主运行模式")
    print("=" * 60)
    
    tool_results = None
    turn = 0
    max_turns = 20
    
    while turn < max_turns:
        turn += 1
        print(f"\n[Turn {turn}] 生成 prompt...")
        
        prompt = build_prompt(task, tool_results, turn)
        messages = [{"role": "user", "content": prompt}]
        
        print(f"[Turn {turn}] 调用 LLM...")
        response = call_llm(messages)
        if response is None:
            print("[错误] LLM API 调用失败（检查 API key）")
            return {"success": False, "error": "LLM call failed"}
        
        print(f"[Turn {turn}] 收到 LLM 回复 ({len(response)} chars)")
        
        parsed = parse_response(response)
        
        if parsed["action"] != "tool_call":
            print(f"\n[完成] 任务完成，{turn} 轮")
            return {"success": True, "content": parsed.get("content", ""), "turns": turn}
        
        tool_calls = parsed.get("tool_calls", [])
        print(f"[Turn {turn}] 执行 {len(tool_calls)} 个工具...")
        
        results = []
        for tc in tool_calls:
            tool_name = tc.get("tool")
            params = tc.get("params", {})
            print(f"  → {tool_name}", end="")
            
            res = registry.execute(tool_name, **params)
            results.append({"tool": tool_name, "params": params, "result": res})
            
            ok = res.get("success", False)
            info = res.get('result', res.get('error', ''))
            print(f" → {'OK' if ok else 'FAIL'}: {str(info)[:80]}")
        
        tool_results = results
    
    return {"success": False, "error": "max turns", "turns": turn}


# ============ 入口 ============

if __name__ == '__main__':
    task = """请找本机的 AFSIM 2.9.0 仿真源码，然后去读相关关于弹道导弹仿真的部分，并做一个弹道，从北京到台北。

步骤：
1. 列出目录 D:\\afsim-2.9.0-win64\\swdev\\src\\wsf_plugins\\wsf_fires\\source\\ 的文件
2. 读 FiresPath.cpp 理解弹道模型
3. 用 python_run 计算从北京(39.9°N, 116.4°E)到台北(25.0°N, 121.5°E)的弹道
4. 输出结果

AFSIM 源码：D:\\afsim-2.9.0-win64\\swdev\\src\\wsf_plugins\\wsf_fires\\source\\"""
    
    print(f"任务：{task[:60]}...\n")
    
    start = time.time()
    result = run_task(task)
    elapsed = time.time() - start
    
    print("\n" + "=" * 60)
    print(f"结果：{'成功' if result.get('success') else '失败'}")
    print(f"耗时：{elapsed:.1f}s，轮次：{result.get('turns', '?')}")
    content = result.get('content', '')
    if content:
        print(f"答案：\n{content[:1000]}")
    print("=" * 60)
"""
Task 1 测试: parse_response 支持多种格式
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import json

def parse_response(raw: str) -> dict:
    """
    解析 response.txt 的内容，支持多种格式：
    1. 纯文本 -> {"content": raw, "action": "final"}
    2. JSON with result -> 提取 result 转 content
    3. JSON with content -> 直接返回
    4. JSON with think/action/tools -> 转为 tool_calls 格式
    """
    if not raw or not raw.strip():
        return {"content": "", "action": "final", "tool_calls": []}

    raw = raw.strip()

    # 如果不是 JSON，当纯文本处理
    if not raw.startswith('{'):
        return {"content": raw, "action": "final", "tool_calls": []}

    # 尝试解析 JSON
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # JSON 解析失败，当纯文本处理
        return {"content": raw, "action": "final", "tool_calls": []}

    # 已有 content 字段
    if 'content' in data:
        if data.get('tool_calls'):
            return {
                "content": data.get('content', ''),
                "action": "tool_call",
                "tool_calls": data['tool_calls']
            }
        return {"content": data['content'], "action": "final", "tool_calls": []}

    # hermes-agent 格式: result -> content
    if 'result' in data:
        return {"content": data['result'], "action": "final", "tool_calls": []}

    # think/action 格式（我们的 prompt 约定的格式）
    if 'think' in data and 'action' in data:
        action = data['action']
        if action == 'tool_call' and 'tools' in data:
            return {
                "content": data.get('think', ''),
                "action": "tool_call",
                "tool_calls": data['tools']
            }
        elif action == 'final':
            return {
                "content": data.get('answer', ''),
                "action": "final",
                "tool_calls": []
            }

    # 其他 JSON 格式，当纯文本
    return {"content": raw, "action": "final", "tool_calls": []}


def test_suite():
    tests = [
        # (描述, 输入, 期望 action, 期望 content 开头)
        ("纯文本", "这是LLM的回复", "final", "这是LLM"),
        ("纯文本长", "我需要读取README.md文件", "final", "我需要读取"),
        ("JSON content final", '{"content": "最终答案", "tool_calls": []}', "final", "最终答案"),
        ("JSON content tool", '{"content": "我要调用工具", "tool_calls": [{"tool": "file_read", "params": {"path": "a.txt"}}]}', "tool_call", "我要调用工具"),
        ("hermes result", '{"success": true, "result": "任务完成", "tool_results": []}', "final", "任务完成"),
        ("think+tool_call", '{"think": "需要读文件", "action": "tool_call", "tools": [{"tool": "file_read", "params": {"path": "a.txt"}}]}', "tool_call", "需要读文件"),
        ("think+final", '{"think": "思考", "action": "final", "answer": "答案是42"}', "final", "答案是42"),
        ("空字符串", "", "final", ""),
        ("空白", "   ", "final", ""),
    ]

    passed = 0
    failed = 0
    for desc, inp, exp_action, exp_content_start in tests:
        result = parse_response(inp)
        ok = result['action'] == exp_action and result['content'].startswith(exp_content_start[:10])
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {desc}")
        if not ok:
            print(f"  期望: action={exp_action}, content startswith '{exp_content_start[:10]}'")
            print(f"  实际: action={result['action']}, content='{result['content'][:30]}'")
            failed += 1
        else:
            passed += 1
    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


if __name__ == "__main__":
    ok = test_suite()
    exit(0 if ok else 1)

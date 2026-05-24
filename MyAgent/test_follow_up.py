"""
MyAgent 追问能力测试 - 手动模拟多轮对话
不走 REPL，直接调用内部方法统计轮数。
"""
import sys, os, json
sys.path.insert(0, r'C:\Users\15041\.openclaw\workspace\MyAgent')

from agent import loop_v2, config, persona, session as sess_module
from agent.loop_v2 import parse_response

# 4 轮追问输入
CONVERSATION_INPUTS = [
    "查看 C:\\Users\\15041\\afsim-wiki\\wiki 目录下的文件，了解 AFSIM 如何仿真弹道导弹",
    "具体说说 Fire PDU 和 Detonation PDU 的字段结构，以及如何关联",
    "如果我要仿真北京到台北的弹道导弹攻击，AFSIM 侧需要做什么配置？Python 侧呢？",
    "弹道计算在哪一层做？AFSIM 内部有弹道计算模型吗？",
]

# 预制 LLM 回复
LLM_RESPONSES = [
    json.dumps({
        "think": "用户想了解 AFSIM 如何仿真弹道导弹。先查看 wiki 目录结构和 index.md 获取概览。",
        "action": "tool_call",
        "tools": [{"tool": "file_read", "params": {"path": "C:\\Users\\15041\\afsim-wiki\\wiki\\index.md"}}]
    }),
    json.dumps({
        "think": "从 index.md 看到了 DIS 协议介绍。现在深入了解 Fire PDU 结构来理解弹道导弹发射流程。",
        "action": "tool_call",
        "tools": [{"tool": "file_read", "params": {"path": "C:\\Users\\15041\\afsim-wiki\\wiki\\dis-fire-pdu.md"}}]
    }),
    json.dumps({
        "think": "用户追问北京到台北场景的具体配置。需要查看 kill-chain-sim 的配置文件。",
        "action": "tool_call",
        "tools": [{"tool": "file_read", "params": {"path": "C:\\Users\\15041\\.openclaw\\workspace\\kill-chain-sim\\src\\sim\\kill_chain_simple.txt"}}]
    }),
    json.dumps({
        "think": "用户问弹道计算在哪层做。根据之前读到的源码，弹道计算在 Python 侧执行，AFSIM 只负责交战。",
        "action": "final",
        "answer": "弹道计算在 Python 侧（kill-chain-sim 的 fire_control.py）执行，AFSIM 内部没有弹道计算模型。AFSIM 是一个交战仿真框架，通过 DIS Fire PDU 接收发射指令，然后通过 WsfDisFire::Process() 创建 WeaponEngagement 来处理交战和毁伤评估。真正的弹道轨迹计算、速度向量、初速等都由外部（Python kill-chain-sim）通过 DIS 协议传给 AFSIM。\n\n简单总结：Python 侧算弹道 → 发 Fire PDU → AFSIM 追踪和交战 → 回报 Detonation PDU。"
    }),
]

def run_conversation():
    """手动跑多轮对话，返回统计结果"""
    # 初始化组件（跳过 REPL 循环）
    cfg = config.AgentConfig()

    # Session
    io_dir = r'C:\Users\15041\.openclaw\workspace\MyAgent\captured_io'
    os.makedirs(io_dir, exist_ok=True)
    session_file = os.path.join(io_dir, 'session.json')

    # 清理旧 session
    if os.path.exists(session_file):
        os.remove(session_file)

    # 创建新 session
    session = sess_module.Session(session_file)
    session.initialize()
    session.save()

    # Persona
    per = persona.Persona()

    # Registry
    from tools import get_initialized_registry
    registry = get_initialized_registry()

    # Memory
    from agent import memory as mem_module
    memory = mem_module.Memory()

    # 统计
    round_num = 0
    tool_call_total = 0
    tool_results_accumulated = []

    print("=" * 60)
    print("MyAgent 追问能力测试 - 多轮对话")
    print("=" * 60)
    print(f"任务：AFSIM 弹道导弹仿真追问测试")
    print(f"输入轮数：{len(CONVERSATION_INPUTS)}")
    print()

    for i, user_input in enumerate(CONVERSATION_INPUTS):
        round_num += 1
        print(f"\n[输入 {round_num}] {user_input[:50]}...")

        # 构建 prompt（简化版，不调用真实方法避免循环依赖）
        prompt = f"[Turn {round_num}] 用户输入: {user_input}\n历史工具结果:\n" + "\n".join([
            f"- {tr['tool']}: {tr.get('result', {})}" for tr in tool_results_accumulated[-5:]
        ])

        # 保存到 prompt.txt
        prompt_file = os.path.join(io_dir, 'prompt.txt')
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt)

        # 注入 LLM 回复到 response.txt
        resp_file = os.path.join(io_dir, 'response.txt')
        with open(resp_file, 'w', encoding='utf-8') as f:
            f.write(LLM_RESPONSES[i])

        # 读取 response.txt，模拟 _wait_for_response 的效果
        with open(resp_file, 'r', encoding='utf-8') as f:
            response_text = f.read()

        # 解析 response
        parsed = parse_response(response_text)
        action = parsed.get("action", "final")

        print(f"[Round {round_num}] 解析动作: {action}")

        if action == "tool_call":
            tool_calls = parsed.get("tool_calls", [])
            print(f"[工具] 检测到 {len(tool_calls)} 个工具调用")

            # 执行工具
            for j, tc in enumerate(tool_calls, 1):
                tool_name = tc.get("tool", "")
                params = tc.get("params", {})
                tool_call_total += 1

                print(f"  {tool_call_total}. {tool_name}: {str(params)[:50]} ... ", end="", flush=True)
                result = registry.execute(tool_name, **params)
                ok = result.get("success", False)

                if ok:
                    print("OK")
                    res_val = result.get("result", result.get("output", ""))
                    tool_results_accumulated.append({
                        "tool": tool_name,
                        "params": params,
                        "result": res_val
                    })
                else:
                    err = result.get("error", "unknown")
                    print(f"FAIL ({err[:30]})")
                    tool_results_accumulated.append({
                        "tool": tool_name,
                        "params": params,
                        "result": f"ERROR: {err}"
                    })

        else:  # final
            final_content = parsed.get("content", "")
            print(f"[完成] 最终答案: {final_content[:100]}...")

    print()
    print("=" * 60)
    print(f"测试完成")
    print(f"总 LLM 调用次数（Round 数）：{round_num}")
    print(f"工具调用总次数：{tool_call_total}")
    print(f"最终答案：\n{final_content}")
    print("=" * 60)

if __name__ == '__main__':
    run_conversation()

    # 清理测试文件
    try:
        os.remove(r'C:\Users\15041\.openclaw\workspace\MyAgent\test_follow_up.py')
    except:
        pass
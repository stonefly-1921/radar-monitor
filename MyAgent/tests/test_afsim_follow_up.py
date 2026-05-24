"""
MyAgent 4轮追问测试 - AFSIM 弹道导弹仿真场景
测试多轮对话中的追问能力，统计 LLM 调用次数和工具调用次数。
"""
import sys
import os
import json
import tempfile
import shutil
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent.loop_v2 import AgentLoopV2


# 4轮追问场景
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


class TestAFSIMFollowUp:
    """测试 AFSIM 弹道导弹仿真场景的4轮追问"""

    def test_four_round_follow_up(self):
        """
        测试4轮追问场景：
        Round 1: 查看 wiki 目录 → file_read index.md
        Round 2: 追问 Fire PDU 结构 → file_read dis-fire-pdu.md
        Round 3: 追问北京到台北场景配置 → file_read kill_chain_simple.txt
        Round 4: 追问弹道计算在哪层 → final answer

        验证：
        - 总 LLM 调用次数 = 4
        - 总工具调用次数 = 3
        - 最终答案是弹道计算在 Python 侧
        """
        base = os.path.join(tempfile.gettempdir(), "myagent_test_afsim_" + str(os.getpid()))
        io_dir = os.path.join(base, "io")
        os.makedirs(io_dir, exist_ok=True)

        try:
            loop = AgentLoopV2()
            loop.base_dir = base
            loop._testing_mode = True
            loop._testing_input_queue = list(CONVERSATION_INPUTS)
            loop._testing_response_queue = list(LLM_RESPONSES)

            result = loop.rewrite_main_loop()

            # 验证返回结果
            assert result is not None, f"Expected result dict, got {result}"
            assert result["iterations"] == 4, f"Expected 4 LLM calls, got {result['iterations']}"
            assert result["tool_calls"] == 3, f"Expected 3 tool calls, got {result['tool_calls']}"

            # 验证 session 记录
            session_path = os.path.join(io_dir, "session.json")
            with open(session_path, 'r', encoding='utf-8') as f:
                session = json.load(f)

            turns = session.get("turns") or []
            assert len(turns) == 4, f"Expected 4 turns, got {len(turns)}"

            # 验证每轮输入
            for i, expected_input in enumerate(CONVERSATION_INPUTS):
                assert turns[i].get("input") == expected_input, \
                    f"Turn {i+1} input mismatch: {turns[i].get('input')} != {expected_input}"

            # 验证工具调用分布在各轮
            tool_calls_all = []
            for turn in turns:
                for tc in turn.get("tool_calls", []):
                    tool_calls_all.append(tc["tool"])

            assert "file_read" in tool_calls_all
            assert len(tool_calls_all) == 3, f"Expected 3 total tool calls, got {len(tool_calls_all)}"

            # 验证最终答案
            final_answer = turns[-1].get("final_answer", "")
            assert "Python" in final_answer and "弹道计算" in final_answer, \
                f"Final answer missing key content: {final_answer[:100]}"

        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_round_by_round_tool_call(self):
        """
        逐轮验证工具调用：
        Round 1 → file_read index.md
        Round 2 → file_read dis-fire-pdu.md
        Round 3 → file_read kill_chain_simple.txt
        Round 4 → no tool (final)
        """
        base = os.path.join(tempfile.gettempdir(), "myagent_test_afsim_rbr_" + str(os.getpid()))
        io_dir = os.path.join(base, "io")
        os.makedirs(io_dir, exist_ok=True)

        try:
            loop = AgentLoopV2()
            loop.base_dir = base
            loop._testing_mode = True
            loop._testing_input_queue = list(CONVERSATION_INPUTS)
            loop._testing_response_queue = list(LLM_RESPONSES)

            result = loop.rewrite_main_loop()

            session_path = os.path.join(io_dir, "session.json")
            with open(session_path, 'r', encoding='utf-8') as f:
                session = json.load(f)

            turns = session.get("turns") or []

            # Round 1: 1 tool call (index.md)
            assert len(turns[0]["tool_calls"]) == 1
            assert "index.md" in turns[0]["tool_calls"][0]["params"]["path"]

            # Round 2: 1 tool call (dis-fire-pdu.md)
            assert len(turns[1]["tool_calls"]) == 1
            assert "dis-fire-pdu.md" in turns[1]["tool_calls"][0]["params"]["path"]

            # Round 3: 1 tool call (kill_chain_simple.txt)
            assert len(turns[2]["tool_calls"]) == 1
            assert "kill_chain_simple.txt" in turns[2]["tool_calls"][0]["params"]["path"]

            # Round 4: no tool (final answer)
            assert len(turns[3]["tool_calls"]) == 0
            assert turns[3].get("final_answer") is not None

        finally:
            shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
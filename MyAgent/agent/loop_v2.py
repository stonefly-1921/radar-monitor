"""
Agent Loop v2 - REPL 交互循环

完全重写为主循环模式：
1. 用户在 input.txt 写任务，按回车
2. 程序生成 prompt.txt（纯文本），用户复制到 LLM
3. 用户把 LLM 回复粘贴到 response.txt，按回车
4. 程序解析并执行工具（显示步骤编号）
5. 多轮循环直到最终答案
6. 完成后回到 input 层等新任务

核心原则：每步都有中文提示，工具执行显示编号。
"""

import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent.persona import Persona
from agent.config import AgentConfig
from memory.core import Memory
from session import Session
from tools import get_initialized_registry


# =============================================================================
# Response 解析函数（来自 tests/test_response_parsing.py，已通过测试）
# =============================================================================

def parse_response(raw: str) -> dict:
    """
    解析 response.txt 的内容，支持多种格式：
    1. 纯文本 -> {"content": raw, "action": "final", "tool_calls": []}
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

    # think/action 格式（prompt 约定的格式）
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


# =============================================================================
# AgentLoopV2 - REPL 主循环
# =============================================================================

class AgentLoopV2:
    """
    MyAgent REPL 交互循环。

    文件映射（纯文本）：
    - io/input.txt: 用户写任务
    - io/prompt.txt: 生成的提示词（供用户复制到 LLM）
    - io/response.txt: LLM 回复（用户粘贴到这里）
    - io/session.json: 会话持久化
    - io/tool_result.json: 工具结果（保留）
    """

    def __init__(self, config=None, llm_client=None):
        self.config = config or AgentConfig()
        self.persona = Persona()
        self.registry = get_initialized_registry()
        self.llm_client = llm_client  # Direct API client for auto mode (保留但不用)

        self.session = None
        self.memory = None

        # I/O 路径 - 全部用 .txt 纯文本
        self.io_config = {
            "input_file": "io/input.txt",
            "prompt_file": "io/prompt.txt",
            "response_file": "io/response.txt",
            "session_file": "io/session.json",
            "tool_result_file": "io/tool_result.json"
        }

        self.base_dir = os.path.dirname(os.path.dirname(__file__))

    def _resolve_path(self, filename):
        return os.path.join(self.base_dir, filename)

    # =========================================================================
    # 初始化
    # =========================================================================

    def initialize(self):
        """初始化 session 和 memory。"""
        print("\n" + "=" * 60)
        print("  MyAgent v2")
        print("=" * 60)

        # 清理旧的 I/O 文件（保留 session.json）
        io_dir = self._resolve_path("io")
        os.makedirs(io_dir, exist_ok=True)
        for f in ["input.txt", "prompt.txt", "response.txt", "tool_result.json"]:
            fpath = os.path.join(io_dir, f)
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception:
                    pass

        # Session
        session_file = self._resolve_path(self.io_config["session_file"])
        self.session = Session.load_or_create(session_file)
        print(f"\n[会话] ID={self.session.session_id}, 轮次={self.session.turn_count}")

        # Memory
        self.memory = Memory()
        if self.session.memory and any(self.session.memory.values()):
            self.memory.load_from_session(self.session.to_dict())

        # Tools
        tools = self.registry.list_tools()
        print(f"[工具] {len(tools)} 个可用: {', '.join(sorted(tools))}")

        print()

    # =========================================================================
    # 工具 spec 列表格式化
    # =========================================================================

    def _format_tools_list(self) -> str:
        """把工具列表格式化为可读的纯文本。"""
        specs = self.registry.get_all_specs()
        lines = []
        for s in specs:
            lines.append(f"- {s['name']}: {s.get('description', '')}")
            if s.get('parameters'):
                for p in s['parameters']:
                    req = "(必填)" if p.get('required') else "(可选)"
                    lines.append(f"  - {p['name']} {req}: {p.get('description', '')}")
        return "\n".join(lines)

    # =========================================================================
    # Prompt 生成 - 输出纯文本 prompt.txt
    # =========================================================================

    def build_prompt_text(self, user_input: str, turn: int, tool_results: list, conversation: list) -> str:
        """
        生成纯文本格式的 prompt.txt。

        格式：
        - 开头说明身份和当前任务
        - 告诉 LLM 输出格式（JSON，人可读）
        - 包含对话历史
        - 包含可用工具列表
        """
        # 系统提示
        system = self.persona.get_system_prompt()

        # 对话历史
        history_lines = []
        if conversation:
            for msg in conversation:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if role == 'user':
                    history_lines.append(f"[用户]: {content}")
                else:
                    history_lines.append(f"[助手]: {content}")
        history_text = "\n".join(history_lines) if history_lines else "(无历史)"

        # 工具结果（如果有）
        tool_results_text = ""
        if tool_results:
            tool_results_text = "\n\n【上次工具执行结果】\n"
            for tr in tool_results:
                name = tr.get('tool', 'unknown')
                params = tr.get('params', {})
                result = tr.get('result', {})
                success = result.get('success', False)
                if success:
                    res_val = result.get('result', result.get('output', ''))
                    tool_results_text += f"- {name}({params}) = {str(res_val)[:100]}\n"
                else:
                    err = result.get('error', 'unknown')
                    tool_results_text += f"- {name}({params}) = FAIL: {err}\n"

        # 工具列表
        tools_list = self._format_tools_list()

        # 完整 prompt
        prompt = f"""{system}

【当前任务】(第 {turn} 轮)
{user_input}
{tool_results_text}

【对话历史】
{history_text}

【可用工具】
{tools_list}

【输出格式要求】
完成思考后，严格按以下格式返回（不要输出任何其他内容）:

# 需要工具时:
{{"think": "你的思考", "action": "tool_call", "tools": [{{"tool": "工具名", "params": {{"参数": "值"}}}}]}}

# 最终答案时:
{{"think": "你的思考", "action": "final", "answer": "你的回答"}}
"""
        return prompt

    def _save_prompt(self, prompt_text: str):
        """保存 prompt.txt。"""
        prompt_file = self._resolve_path(self.io_config["prompt_file"])
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt_text)

    # =========================================================================
    # REPL 主循环
    # =========================================================================

    def rewrite_main_loop(self):
        """REPL 主循环入口。"""
        self.initialize()

        while True:
            # === input 层 ===
            print("\n" + "=" * 60)
            print("  MyAgent v2")
            print("=" * 60)
            print("请在 input.txt 写任务，输入 quit 退出")
            print()

            # 等待用户写 input.txt 并敲回车
            user_input = self._wait_for_input()
            if user_input == "quit":
                print("[退出] 再见！")
                break

            # === 任务执行层（可能多轮）===
            self._execute_task(user_input)
            # 任务完成后自动回到 input 层等新任务

    def _wait_for_input(self) -> str:
        """
        等待用户准备 input.txt。
        用户敲回车后读取 input.txt 内容。
        直接输入 quit 字符串则退出程序。
        """
        input("按回车继续（输入 quit 退出）...\n")

        # 检查是否要退出
        # 注意：用户输入 quit 时，input() 会返回 "quit"
        # 但我们用文件模式，用户在 input.txt 里写 quit 才是取消任务
        # 这里 stdin 的 quit 是退出程序

        input_file = self._resolve_path(self.io_config["input_file"])

        # 如果文件不存在，等用户创建
        while not os.path.exists(input_file):
            print("[等待] 请在 input.txt 写任务...")
            input("按回车继续...\n")

        # 读取内容
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()

        # 空内容，继续等
        if not content:
            # 清空并继续等待
            print("[提示] input.txt 为空，请写入任务")
            return self._wait_for_input()

        # 清空 input.txt（用户自己管）
        try:
            with open(input_file, 'w', encoding='utf-8') as f:
                f.write('')
        except Exception:
            pass

        return content

    def _wait_for_response(self) -> str:
        """
        等待用户粘贴 LLM 回复到 response.txt。
        用户敲回车后读取 response.txt。
        如果文件不存在或为空，持续等待。
        如果内容是 quit 字符串，取消当前任务。
        """
        response_file = self._resolve_path(self.io_config["response_file"])

        while True:
            if os.path.exists(response_file):
                with open(response_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()

                if content:
                    # 清空 response.txt
                    try:
                        with open(response_file, 'w', encoding='utf-8') as f:
                            f.write('')
                    except Exception:
                        pass
                    return content

            print("[等待] 请把 LLM 回复粘贴到 response.txt...")
            input("按回车继续...\n")

    def _do_summary(self):
        """
        执行 LLM 摘要流程。
        当 memory.get_needs_summary() 为 True 时调用。
        
        流程：
        1. 生成 summary_prompt.txt（包含待摘要的对话历史）
        2. 提示用户复制到 LLM
        3. 等待用户粘贴 LLM 摘要到 summary_response.txt
        4. 读取摘要，调用 compress_conversation
        """
        print("\n[摘要] 对话过长，需要生成摘要...")
        
        # 获取待摘要的对话历史
        ctx = self.memory.get_summary_context()
        
        # 生成摘要提示词
        summary_prompt = f"""请总结以下对话的要点，要求：
1. 100字以内
2. 只返回摘要文字，不要其他内容
3. 涵盖主要内容和关键结论

---对话历史---
{ctx['history_text']}
---结束---

摘要："""
        
        # 写入 summary_prompt.txt
        prompt_file = self._resolve_path("io/summary_prompt.txt")
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(summary_prompt)
        
        print(f"[生成] 摘要提示词已写入 summary_prompt.txt ({ctx['history_lines']} 轮对话)")
        print(f"[下一步] 请复制 summary_prompt.txt 内容到 LLM")
        print(f"[等待] 把 LLM 的摘要粘贴到 summary_response.txt，按回车继续...")
        input()
        
        # 读取 LLM 摘要
        summary_file = self._resolve_path("io/summary_response.txt")
        if os.path.exists(summary_file):
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary_text = f.read().strip()
            # 清空文件
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write('')
        else:
            summary_text = "[摘要内容为空]"
        
        print(f"[摘要] 已收到摘要: {summary_text[:50]}...")
        
        # 执行压缩
        self.memory.compress_conversation(summary_text)
        self.memory.set_needs_summary(False)
        print(f"[摘要] 对话已压缩，当前 {self.memory.turn_count} 轮")

    def _execute_task(self, user_input: str):
        """
        执行任务，可能多轮循环。

        流程：
        1. 生成 prompt.txt，显示提示
        2. 等待用户粘贴 response.txt
        3. 解析 response
        4. 如果是工具调用，执行并显示步骤
        5. 如果是最终答案，显示并结束
        """
        turn = 1
        tool_results = None

        # 保存用户输入到 session
        self.session.add_turn({"input": user_input})
        self.session.save()

        while True:
            # === Token 超限检查：需要摘要时先做摘要 ===
            if self.memory.get_needs_summary():
                self._do_summary()

            # === 生成 prompt.txt ===
            conversation = self.session.get_conversation_history()
            prompt_text = self.build_prompt_text(
                user_input=user_input,
                turn=turn,
                tool_results=tool_results,
                conversation=conversation
            )
            self._save_prompt(prompt_text)

            print(f"\n[生成] 提示词已写入 prompt.txt，请复制到 LLM")
            print(f"[等待] 把 LLM 回复粘贴到 response.txt，按回车继续...")

            # === 等待用户粘贴回复 ===
            response_text = self._wait_for_response()

            # quit 字符串（用户粘贴了 quit）取消任务
            if response_text.strip().lower() == "quit":
                print("[取消] 当前任务已取消，回到等待输入")
                return

            # === 解析 response ===
            parsed = parse_response(response_text)

            if parsed["action"] == "tool_call":
                # === 执行工具 ===
                tool_calls = parsed.get("tool_calls", [])
                print(f"\n[工具] 检测到 {len(tool_calls)} 个工具调用，执行中...")
                results = self._execute_tools_display(tool_calls)

                # 保存工具结果到 session
                turn_data = self.session.get_last_turn()
                if turn_data:
                    turn_data["tool_calls"] = tool_calls
                    turn_data["tool_results"] = results
                self.session.save()

                # === 工具执行后再次检查是否需要摘要 ===
                if self.memory.get_needs_summary():
                    self._do_summary()

                # 下一轮
                tool_results = results
                turn += 1
                continue

            else:
                # === 最终答案 ===
                final_content = parsed.get("content", "")

                print(f"\n[完成] 任务完成\n")
                print("=" * 60)
                print(f"最终答案:\n{final_content}")
                print("=" * 60)

                # 保存最终答案到 session
                turn_data = self.session.get_last_turn()
                if turn_data:
                    turn_data["final_answer"] = final_content
                self.session.save()

                return  # 回到 input 层

    def _execute_tools_display(self, tool_calls: list) -> list:
        """
        执行工具并显示步骤编号。

        格式：
          1. file_read: {'path': 'a.txt'} ... OK
          2. shell_run: {'cmd': 'dir'} ... FAIL (错误信息)

        Returns:
            list: [{"tool": name, "params": {...}, "result": {...}}, ...]
        """
        results = []
        for i, tc in enumerate(tool_calls, 1):
            tool_name = tc.get("tool")
            params = tc.get("params", {})

            # 显示执行中的状态
            params_str = str(params)
            print(f"  {i}. {tool_name}: {params_str[:60]} ... ", end="", flush=True)

            # 执行工具
            result = self.registry.execute(tool_name, **params)
            ok = result.get("success")

            if ok:
                print("OK")
            else:
                err = result.get("error", "")
                print(f"FAIL ({err[:30] if err else 'unknown'})")

            results.append({
                "tool": tool_name,
                "params": params,
                "result": result
            })

        return results

    # =========================================================================
    # 兼容旧接口（保留但不使用）
    # =========================================================================

    def run(self, user_input: str = None):
        """兼容旧接口，直接进入 REPL 模式。"""
        self.rewrite_main_loop()

    # =========================================================================
    # 入口
    # =========================================================================

    def main(self):
        """主入口 - 直接进入 REPL 模式。"""
        import sys
        is_new = '--new' in sys.argv or '-n' in sys.argv

        if is_new:
            # 清理所有持久化数据
            base = self._resolve_path('io')
            for f in ['session.json', 'memory.json', 'input.txt', 'input.json',
                      'prompt.txt', 'response.txt', 'tool_result.json']:
                fpath = os.path.join(base, f)
                if os.path.exists(fpath):
                    try:
                        os.remove(fpath)
                    except Exception:
                        pass
            print('[NEW] 已清除所有历史记录和缓存文件')
            print()

        self.rewrite_main_loop()


# =============================================================================
# 模块入口
# =============================================================================

def main():
    """文件模式入口点。"""
    loop = AgentLoopV2()
    loop.main()


if __name__ == '__main__':
    main()
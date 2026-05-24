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
# 运行时上下文分隔符（用于在不污染 transcript 的情况下注入内部状态）
# =============================================================================
RUNTIME_CONTEXT_BEGIN = "<<<BEGIN_MYAGENT_INTERNAL_CONTEXT>>>"
RUNTIME_CONTEXT_END = "<<<END_MYAGENT_INTERNAL_CONTEXT>>>"


# =============================================================================
# 工具结果摘要函数（非 LLM，基于规则提取关键行）
# =============================================================================

def _summarize_tool_result(result_text: str, max_chars: int = 5000) -> str:
    """
    智能摘要工具结果：优先保留关键行（错误/公式/常量），再按 max_chars 截断。

    规则：
    1. 如果总长度 <= max_chars，直接返回
    2. 提取含关键词的行（error, fail, traceback, 公式, 数字常量等）
    3. 保留文件开头（前 20 行）
    4. 合并后截断到 max_chars
    """
    if len(result_text) <= max_chars:
        return result_text

    lines = result_text.split('\n')
    key_lines = []

    # 关键词：错误、公式、关键数字
    KEYWORDS = [
        'error', 'fail', 'traceback', 'exception', 'warning',
        'def ', 'class ', 'import ', 'const', 'define',
        'exp(', 'sin(', 'cos(', 'atan(', 'sqrt(',  # 数学公式
        'v0x', 'v0z', 'tc', 'g =', 'dt', 'vz', 'vx',  # 弹道相关符号
        'BALLISTIC', 'MISSILE', 'PATH', 'TRAJECTORY',  # 领域关键词
        'def __init__', 'self.', 'return ', '-> ',  # 代码结构
        '=', ': ',  # 赋值/类型标注
    ]

    for line in lines:
        line_lower = line.lower()
        if any(kw.lower() in line_lower for kw in KEYWORDS):
            key_lines.append(line)

    # 保留开头（通常含文件头/重要定义）
    start_lines = lines[:20]

    # 去重合并
    seen = set()
    merged = []
    for group in [start_lines, key_lines]:
        for line in group:
            if line and line not in seen:
                seen.add(line)
                merged.append(line)

    summarized = '\n'.join(merged)
    if len(summarized) > max_chars:
        summarized = summarized[:max_chars] + f"\n[...内容已截断，原始长度 {len(result_text)} 字符]"
    return summarized


# =============================================================================
# Response 解析函数（来自 tests/test_response_parsing.py，已通过测试）
# =============================================================================

def parse_response(raw: str) -> dict:
    """
    解析 response.txt 的内容，支持多种格式：
    1. 纯文本 -> {"content": raw, "action": "final", "tool_calls": []}
    2. JSON with tool_calls -> 返回 tool_call action
    3. JSON with tool_results (Hermes 格式) -> 转为 tool_calls 返回 tool_call action
    4. JSON with think/action/tools -> 转为 tool_calls 格式
    5. JSON with content + tool_calls -> 优先 tool_calls
    6. JSON with result (Hermes) -> 当 final（无工具时）
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

    # ============================================================
    # 优先检查 tool_calls（最明确的工具调用格式）
    # ============================================================
    if 'tool_calls' in data and data['tool_calls']:
        return {
            "content": data.get('content', ''),
            "action": "tool_call",
            "tool_calls": data['tool_calls']
        }

    # ============================================================
    # 检查 tool_results (Hermes/MyAgent 格式)
    # tool_results = [{"tool": "xxx", "params": {...}, "result": {...}}]
    # ============================================================
    if 'tool_results' in data and data['tool_results']:
        tool_calls = []
        for tr in data['tool_results']:
            if isinstance(tr, dict) and 'tool' in tr:
                tool_calls.append({
                    "tool": tr['tool'],
                    "params": tr.get('params', {})
                })
        if tool_calls:
            return {
                "content": data.get('result', data.get('content', '')),
                "action": "tool_call",
                "tool_calls": tool_calls
            }

    # ============================================================
    # think/action 格式（prompt 约定的格式）
    # ============================================================
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

    # ============================================================
    # 有 content 字段但无工具 -> final answer
    # ============================================================
    if 'content' in data:
        return {"content": data['content'], "action": "final", "tool_calls": []}

    # ============================================================
    # 只有 result 字段 (Hermes 无工具格式) -> final answer
    # ============================================================
    if 'result' in data:
        return {"content": data['result'], "action": "final", "tool_calls": []}

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

        # Testing mode: bypass input() for pytest
        self._testing_mode = False
        self._testing_input_queue = []  # list of strings to return from _wait_for_input
        self._testing_response_queue = []  # list of LLM responses for _wait_for_response

        # Task state for multi-turn optimization (TaskState section in prompt)
        self._task_state = None

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

        # 清理旧的 I/O 文件
        io_dir = self._resolve_path("io")
        os.makedirs(io_dir, exist_ok=True)
        # 每次启动清空所有 IO 文件，保持干净状态
        for f in ["input.txt", "prompt.txt", "response.txt", "tool_result.json"]:
            fpath = os.path.join(io_dir, f)
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception:
                    pass
            # 创建空文件占位
            with open(fpath, 'w', encoding='utf-8') as fh:
                pass

        # Session - 加载后去重
        session_file = self._resolve_path(self.io_config["session_file"])
        self.session = Session.load_or_create(session_file)
        
        # 启动时对 session turns 去重压缩
        if self.session.turns:
            original_count = len(self.session.turns)
            self.session.deduplicate_turns()
            self.session.save()
            if original_count > len(self.session.turns):
                print(f"[整理] 合并重复输入: {original_count} -> {len(self.session.turns)} 轮")
        
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
    # TaskState 管理（用于 prompt 优化）
    # =========================================================================

    def _init_task_state(self, user_input: str):
        """初始化 task_state，在每轮任务开始时调用。"""
        self._task_state = {
            "goal": user_input,
            "turn": 1,
            "steps_taken": [],  # [{"tool": "...", "finding": "..."}, ...]
            "pending": None,
            "errors": [],
        }

    def _update_task_state(self, tool_result: dict, finding: str):
        """每轮工具执行后调用，更新 task_state。"""
        if self._task_state is None:
            return
        tool_name = tool_result.get('tool', 'unknown')
        self._task_state["steps_taken"].append({
            "tool": tool_name,
            "finding": finding,
        })

    def _build_task_state_text(self) -> str:
        """生成 TaskState 块的文本，注入到 prompt。"""
        if self._task_state is None:
            return ""
        ts = self._task_state
        lines = ["【本轮状态】"]
        lines.append(f"- 当前目标: {ts['goal']}")
        lines.append(f"- 轮次: 第 {ts['turn']} 轮")
        if ts["steps_taken"]:
            lines.append("- 已完成:")
            for step in ts["steps_taken"]:
                lines.append(f"  · {step['tool']}: {step['finding']}")
        if ts["pending"]:
            lines.append(f"- 待解决: {ts['pending']}")
        if ts["errors"]:
            lines.append(f"- 错误记录:")
            for err in ts["errors"]:
                lines.append(f"  · {err}")

        # Stuck detection: warn if same tool called 3+ times consecutively
        if len(ts["steps_taken"]) >= 3:
            last_three = ts["steps_taken"][-3:]
            tools = [s["tool"] for s in last_three]
            if tools[0] == tools[1] == tools[2]:
                lines.append(f"\n⚠️ 检测到重复工具调用 [{tools[0]}] 连续 3 次，请重新评估策略或尝试其他方法。")

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

        # 对话历史（超过 10 轮时压缩）
        if conversation:
            if len(conversation) > 10:
                # 压缩：显示早期摘要 + 最近 10 轮
                recent = conversation[-10:]
                total = len(conversation)
                history_lines = [
                    f"[早期对话摘要] 共 {total} 轮，显示最近 10 轮"
                ]
                for msg in recent:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    if role == 'user':
                        history_lines.append(f"[用户]: {content}")
                    else:
                        history_lines.append(f"[助手]: {content[:150]}")  # 截断每条到150字
                history_text = "\n".join(history_lines)
            else:
                history_lines = []
                for msg in conversation:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    if role == 'user':
                        history_lines.append(f"[用户]: {content}")
                    else:
                        history_lines.append(f"[助手]: {content}")
                history_text = "\n".join(history_lines) if history_lines else "(无历史)"
        else:
            history_text = "(无历史)"

        # 工具结果（如果有）—— 智能摘要
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
                    max_chars = self.config.tool_result_max_chars
                    truncated = _summarize_tool_result(str(res_val), max_chars)
                    tool_results_text += f"- {name}({params}) = {truncated}\n"
                else:
                    err = result.get('error', 'unknown')
                    tool_results_text += f"- {name}({params}) = FAIL: {err}\n"

        # TaskState 区域（turn > 1 显示进度）
        task_state_text = self._build_task_state_text() if self._task_state and turn > 1 else ""

        # 反思块（工具执行后强制先分析再决定）
        reflect_text = ""
        if tool_results:
            reflect_text = """
【工具执行结果分析】
你刚执行了工具，分析结果后决定下一步：
- 如果结果已经回答了用户问题 → action: final
- 如果结果不够，说明还需要什么信息/工具
- 如果有错误，分析原因并决定是否重试
"""

        # Memory 摘要（turn > 3 防止上下文膨胀）
        memory_text = ""
        if turn > 3 and self.memory and self.memory.turn_count > 3:
            ctx = self.memory.get_summary_context()
            if ctx and ctx.get('history_text'):
                memory_text = f"\n\n【历史摘要】（防止上下文溢出）\n{ctx['history_text']}\n"

        # 工具列表
        tools_list = self._format_tools_list()

        # 完整 prompt
        prompt = f"""{system}

【当前任务】(第 {turn} 轮)
{user_input}
{task_state_text}
{tool_results_text}
{reflect_text}
{memory_text}

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

【注意】Windows 路径中的反斜杠在 JSON 中需要转义：
- 正确: {{"path": "C:\\\\Users\\\\15041\\\\Desktop"}}
- 错误: {{"path": "C:\\Users\\15041\\Desktop"}}  (缺少转义)
- 错误: {{"path": "C:Users15041Desktop"}}  (没有反斜杠)
"""

        # === 注入运行时上下文（不污染 transcript） ===
        runtime_sections = []

        # Priority 1: Stuck detection warning (already in task_state_text, but also inject here)
        if self._task_state and len(self._task_state["steps_taken"]) >= 3:
            last_three = self._task_state["steps_taken"][-3:]
            if all(s["tool"] == last_three[0]["tool"] for s in last_three):
                runtime_sections.append(
                    f"[警告] 检测到重复工具调用 [{last_three[0]['tool']}] 连续 3 次，请重新评估策略。"
                )

        # Priority 2: Memory compression summary (if needs summary)
        if self.memory and self.memory.get_needs_summary():
            ctx = self.memory.get_summary_context()
            if ctx and ctx.get('history_text'):
                runtime_sections.append(f"[Memory Summary] {ctx['history_text']}")

        # Priority 3: System reminders (if any errors)
        if self._task_state and self._task_state["errors"]:
            runtime_sections.append(f"[Errors] {', '.join(self._task_state['errors'][:3])}")

        if runtime_sections:
            prompt = f"{prompt}\n\n{RUNTIME_CONTEXT_BEGIN}\n" + "\n\n".join(runtime_sections) + f"\n{RUNTIME_CONTEXT_END}"

        return prompt

    def _save_prompt(self, prompt_text: str):
        """保存 prompt.txt。"""
        prompt_file = self._resolve_path(self.io_config["prompt_file"])
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt_text)

    # =========================================================================
    # REPL 主循环
    # =========================================================================

    def rewrite_main_loop(self, user_input: str = None):
        """REPL 主循环入口。
        
        Args:
            user_input: 如果提供，直接用这个输入启动任务（用于测试）。
                       不提供则进入交互式等待模式。
        """
        self.initialize()

        # 测试模式：user_input 直接来自队列，不需要 input.txt 轮询
        if self._testing_mode:
            while True:
                user_input = self._wait_for_input()
                if user_input is None:
                    break
                if user_input == "quit":
                    break
                task_result = self._execute_task(user_input)
                return task_result  # 测试模式：返回任务结果
            return None

        while True:
            # === input 层 ===
            print("\n" + "=" * 60)
            print("  MyAgent v2")
            print("=" * 60)
            print("请在 input.txt 写任务，输入 quit 退出")
            print()

            if user_input is None:
                # 交互模式：等待用户写 input.txt 并敲回车
                user_input = self._wait_for_input()
                if user_input is None:
                    # 队列空，退出 REPL
                    break
            elif self._testing_mode:
                # 测试模式：直接从队列取输入
                user_input = self._wait_for_input()
                if user_input is None:
                    # 队列空，退出 REPL
                    break

            if user_input == "quit":
                print("[退出] 再见！")
                break

            # === 任务执行层（可能多轮）===
            task_result = self._execute_task(user_input)
            # 测试模式：返回任务结果，不继续循环
            if self._testing_mode:
                return task_result
            # 任务完成后，回到交互模式等下一轮
            user_input = None  # 等下一轮任务

    def _wait_for_input(self) -> str:
        """
        等待用户准备 input.txt。
        用户敲回车后读取 input.txt 内容。
        直接输入 quit 字符串则退出程序。

        测试模式下跳过 input() 调用，直接从 _testing_input_queue 取值。
        如果队列为空但 input.txt 有内容，直接读取（Win7 双击场景）。
        返回 None 表示测试结束（队列空且文件也空）。
        Win7 双击场景：优先读 input.txt，有内容就直接执行，不需敲回车。
        """
        if self._testing_mode:
            # 优先从队列取值
            if self._testing_input_queue:
                return self._testing_input_queue.pop(0)
            # 队列空：仍然检查 input.txt（Win7 双击 / echo 管道场景）
            input_file = self._resolve_path(self.io_config["input_file"])
            if os.path.exists(input_file):
                with open(input_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                if content:
                    # 清空文件（防止重复执行）
                    try:
                        with open(input_file, 'w', encoding='utf-8') as f:
                            f.write('')
                    except Exception:
                        pass
                    return content
            return None

        input_file = self._resolve_path(self.io_config["input_file"])

        # === 优先：input.txt 有内容就直接用（Win7 双击 / echo 管道场景）===
        if os.path.exists(input_file):
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            if content:
                try:
                    with open(input_file, 'w', encoding='utf-8') as f:
                        f.write('')
                except Exception:
                    pass
                return content

        # === 非交互环境（无 tty）且文件为空 → 正常跳过，让文件流程处理 ===
        if not sys.stdin.isatty():
            # Win7 双击场景：stdin 无 tty，但文件操作正常
            # 文件有内容 → 在前面读取；文件无内容或不存在 → 等待用户写文件后重试
            pass  # 不退出，继续往下走文件等待逻辑

        # === 正常交互模式：等用户敲回车或输入 quit ===
        try:
            user_quit = input("按回车继续（输入 quit 退出）...\n")
            if user_quit.strip().lower() == "quit":
                return "quit"
        except (EOFError, OSError):
            # 非交互环境（Win7双击 / 重定向 / pytest），安全退出
            print("[退出] 输入流关闭，程序退出")
            return None

        # 敲回车后读文件（正常交互流程）
        if os.path.exists(input_file):
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
        else:
            content = ''

        if not content:
            print("[提示] input.txt 为空，请写入任务")
            return self._wait_for_input()

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
        
        测试模式下优先从 _testing_response_queue 取值（MockLLM 的回复）。
        """
        # 测试模式：优先用队列中的模拟 LLM 回复
        if self._testing_mode:
            if self._testing_response_queue:
                return self._testing_response_queue.pop(0)
            # 测试队列为空：文件也不存在，直接返回 quit 通知上层取消任务
            return "quit"

        response_file = self._resolve_path(self.io_config["response_file"])

        while True:
            if os.path.exists(response_file):
                with open(response_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()

                if content:
                    # 清空 response.txt（防止重复使用）
                    try:
                        with open(response_file, 'w', encoding='utf-8') as f:
                            f.write('')
                    except Exception:
                        pass
                    return content
            else:
                content = ''

            if self._testing_mode:
                # Testing: no queued response AND file doesn't exist or is empty.
                # Return "quit" so caller knows to cancel.
                return "quit"

            if not sys.stdin.isatty():
                # 非交互环境（Win7 双击）：等待用户粘贴文件内容
                # 先检测文件是否存在且有内容，没有则等待
                import time
                if not os.path.exists(response_file):
                    print("[等待] 请把 LLM 回复粘贴到 response.txt...")
                # 文件存在但为空，说明用户正在粘贴中，继续等待
                time.sleep(2)
                continue

            print("[等待] 请把 LLM 回复粘贴到 response.txt...")
            try:
                input("按回车继续...\n")
            except (EOFError, OSError):
                print("[退出] 输入流关闭，程序退出")
                return "quit"

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
        if self._testing_mode:
            summary_text = "[测试摘要]"
        else:
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

        # 初始化 TaskState（用于 prompt 优化）
        self._init_task_state(user_input)

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

            # quit 字符串（用户粘贴了 quit）取消任务，回到 input 层继续等下一轮
            if response_text.strip().lower() == "quit":
                print("[取消] 当前任务已取消，回到等待输入")
                return {"cancelled": True}

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

                # 更新 TaskState（工具结果记录）
                for tr in results:
                    tool_name = tr.get('tool', 'unknown')
                    res = tr.get('result', {})
                    if res.get('success'):
                        finding = str(res.get('result', res.get('output', '')))[:80]
                    else:
                        finding = f"FAIL: {res.get('error', 'unknown')}"
                    self._update_task_state(tr, finding)

                # === 工具执行后再次检查是否需要摘要 ===
                if self.memory.get_needs_summary():
                    self._do_summary()

                # 下一轮
                tool_results = results
                turn += 1
                self._task_state["turn"] = turn
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

                return {
                    "success": True,
                    "content": final_content,
                    "tool_calls": turn - 1,
                    "iterations": turn,
                    "session_id": self.session.session_id if self.session else None
                }  # 回到 input 层

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
        return self.rewrite_main_loop()

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
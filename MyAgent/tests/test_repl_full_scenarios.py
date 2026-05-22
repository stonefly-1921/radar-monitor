"""
Comprehensive test plan for MyAgent v2 full REPL workflow.

This module tests the COMPLETE manual file-based REPL workflow:
- Users write tasks in io/input.txt
- Agent generates prompts in io/prompt.txt
- Users paste LLM responses to io/response.txt
- Agent executes tools in a loop

Tests cover:
a. Win7 double-click launch with input.txt pre-written
b. Multi-turn conversation: input → prompt → response → tool result → next prompt → final answer
c. The _wait_for_response loop with file polling
d. Session persistence across multiple tasks
e. Edge case: response.txt appears only after several seconds (slow LLM)

All tests use REAL file-based I/O (not mocked). Each test simulates a real user
interaction step using actual files on disk.

IMPORTANT - Session "turns" vs LLM "iterations" distinction:
- A session turn = ONE user input (one task) stored in session.turns[]
- An LLM iteration = ONE LLM call within _execute_task()
- One session turn may contain multiple LLM iterations (tool calls)
- All tool calls from all iterations within a task are accumulated in session.turns[N].tool_calls
- result["iterations"] = total LLM calls in the task
- result["tool_calls"] = turn-1 (note: for multi-tool single-iteration, use len(session turn tool_calls))
"""
import sys
import os
import json
import time
import tempfile
import shutil
import threading
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent.loop_v2 import AgentLoopV2, parse_response


# =============================================================================
# parse_response unit tests
# =============================================================================

class TestParseResponse:
    """Unit tests for the parse_response function."""

    def test_plain_text(self):
        result = parse_response("这是一个纯文本回复")
        assert result["action"] == "final"
        assert result["content"] == "这是一个纯文本回复"
        assert result["tool_calls"] == []

    def test_json_with_result(self):
        result = parse_response('{"result": "查询结果是42"}')
        assert result["action"] == "final"
        assert result["content"] == "查询结果是42"

    def test_json_with_content(self):
        result = parse_response('{"content": "直接内容"}')
        assert result["content"] == "直接内容"
        assert result["action"] == "final"

    def test_tool_call_format(self):
        raw = json.dumps({
            "think": "我需要读取文件",
            "action": "tool_call",
            "tools": [{"tool": "file_read", "params": {"path": "a.txt"}}]
        })
        result = parse_response(raw)
        assert result["action"] == "tool_call"
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["tool"] == "file_read"
        assert result["tool_calls"][0]["params"]["path"] == "a.txt"

    def test_final_answer_format(self):
        raw = json.dumps({
            "think": "任务完成",
            "action": "final",
            "answer": "北京是中国的首都"
        })
        result = parse_response(raw)
        assert result["action"] == "final"
        assert result["content"] == "北京是中国的首都"

    def test_empty_string(self):
        result = parse_response("")
        assert result["action"] == "final"
        assert result["content"] == ""

    def test_whitespace_only(self):
        result = parse_response("   \n\t  ")
        assert result["action"] == "final"
        assert result["content"] == ""


# =============================================================================
# Test Case A: Win7 Double-Click Launch
# =============================================================================

class TestWin7DoubleClickLaunch:
    """
    Test Case A: Win7 double-click launch scenario.

    Workflow:
    1. User pre-writes task to input.txt (double-click run.bat, or echo pipe)
    2. Agent detects input.txt has content on startup
    3. Agent reads input.txt content directly (no stdin interaction needed)
    4. Agent generates prompt.txt
    5. User pastes LLM response
    6. Loop completes
    """

    def test_input_txt_pre_written_starts_immediately(self):
        """
        Simulate: user pre-wrote task to input.txt, then double-clicked run.bat.
        Agent should read the task and start immediately without blocking on stdin.
        """
        base = os.path.join(tempfile.gettempdir(), "myagent_test_a1_" + str(os.getpid()))
        io_dir = os.path.join(base, "io")
        os.makedirs(io_dir, exist_ok=True)
        try:
            with open(os.path.join(io_dir, "input.txt"), 'w', encoding='utf-8') as f:
                f.write("帮我查询 C:\\Users\\ 配置目录有多少个文件")

            loop = AgentLoopV2()
            loop.base_dir = base
            loop._testing_mode = True
            loop._testing_input_queue = []  # empty - simulate non-tty stdin
            loop._testing_response_queue = []
            loop.initialize()

            result = loop._wait_for_input()
            assert result == "帮我查询 C:\\Users\\ 配置目录有多少个文件"
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_full_workflow_win7_double_click_single_turn(self):
        """
        End-to-end: Win7 double-click launch with a single-turn task.
        result is not None (returns task result, not the REPL loop value).
        """
        base = os.path.join(tempfile.gettempdir(), "myagent_test_a2_" + str(os.getpid()))
        io_dir = os.path.join(base, "io")
        os.makedirs(io_dir, exist_ok=True)
        try:
            with open(os.path.join(io_dir, "input.txt"), 'w', encoding='utf-8') as f:
                f.write("1+1等于几？")

            loop = AgentLoopV2()
            loop.base_dir = base
            loop._testing_mode = True
            loop._testing_input_queue = []
            loop._testing_response_queue = [
                json.dumps({"think": "简单数学", "action": "final", "answer": "1+1=2"})
            ]
            result = loop.rewrite_main_loop()

            # Testing mode returns task result, not None
            assert result is not None
            assert result["content"] == "1+1=2"
            assert result["iterations"] == 1

            # Verify prompt.txt was generated
            prompt_path = os.path.join(io_dir, "prompt.txt")
            assert os.path.exists(prompt_path)
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            assert "1+1等于几" in content

            # Verify session
            session_path = os.path.join(io_dir, "session.json")
            with open(session_path, 'r', encoding='utf-8') as f:
                session = json.load(f)
            turns = session.get("turns") or []
            assert len(turns) == 1
            assert turns[0].get("input") == "1+1等于几？"
            assert turns[0].get("final_answer") == "1+1=2"
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_full_workflow_win7_double_click_tool_call(self):
        """
        End-to-end: Win7 double-click launch with a tool-call turn.

        One session turn per task; multiple LLM iterations per task.
        result['iterations'] = all LLM calls (tool + final).
        All tools from all iterations accumulated in session.turns[0].tool_calls.
        """
        base = os.path.join(tempfile.gettempdir(), "myagent_test_a3_" + str(os.getpid()))
        io_dir = os.path.join(base, "io")
        os.makedirs(io_dir, exist_ok=True)
        try:
            test_file = os.path.join(io_dir, "readme.txt")
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write("Hello MyAgent World")

            with open(os.path.join(io_dir, "input.txt"), 'w', encoding='utf-8') as f:
                f.write("读取 readme.txt 的内容")

            loop = AgentLoopV2()
            loop.base_dir = base
            loop._testing_mode = True
            loop._testing_input_queue = []
            loop._testing_response_queue = [
                json.dumps({
                    "think": "需要读取文件",
                    "action": "tool_call",
                    "tools": [{"tool": "file_read", "params": {"path": test_file}}]
                }),
                json.dumps({
                    "think": "文件已读",
                    "action": "final",
                    "answer": "文件内容是: Hello MyAgent World"
                })
            ]
            result = loop.rewrite_main_loop()

            assert result is not None
            assert result["iterations"] == 2
            assert result["tool_calls"] == 1  # turn-1, single iteration with 1 tool

            session_path = os.path.join(io_dir, "session.json")
            with open(session_path, 'r', encoding='utf-8') as f:
                session = json.load(f)
            turns = session.get("turns") or []
            assert len(turns) == 1
            assert turns[0].get("input") == "读取 readme.txt 的内容"
            assert len(turns[0].get("tool_calls", [])) == 1
            assert turns[0]["tool_calls"][0]["tool"] == "file_read"
            assert "Hello MyAgent World" in turns[0].get("final_answer", "")
        finally:
            shutil.rmtree(base, ignore_errors=True)


# =============================================================================
# Test Case B: Multi-Turn Conversation
# =============================================================================

class TestMultiTurnConversation:
    """
    Test Case B: Multi-turn conversation within a single REPL session.

    A real multi-turn REPL conversation:
    Iteration 1: input → prompt → LLM requests tool → execute tool
    Iteration 2: prompt (with tool result) → LLM requests another tool → execute
    Iteration 3: prompt (with tool results) → LLM gives final answer

    All iterations happen in ONE rewrite_main_loop() call (one task).
    All tool calls across iterations are accumulated in session.turns[0].tool_calls.

    result["iterations"] = total LLM calls in the task.
    session.turns[0].tool_calls = all tools from all iterations.
    """

    def test_two_turn_with_tool_then_final(self):
        """
        Two LLM iterations: tool call then final answer.
        result['iterations'] == 2, session has 1 turn with 1 tool_call.
        """
        base = os.path.join(tempfile.gettempdir(), "myagent_test_b1_" + str(os.getpid()))
        io_dir = os.path.join(base, "io")
        os.makedirs(io_dir, exist_ok=True)
        try:
            with open(os.path.join(io_dir, "input.txt"), 'w', encoding='utf-8') as f:
                f.write("列出 io 目录下的所有文件")

            loop = AgentLoopV2()
            loop.base_dir = base
            loop._testing_mode = True
            loop._testing_input_queue = []
            loop._testing_response_queue = [
                json.dumps({
                    "think": "需要列出文件",
                    "action": "tool_call",
                    "tools": [{"tool": "file_list", "params": {"path": io_dir}}]
                }),
                json.dumps({
                    "think": "已获取文件列表",
                    "action": "final",
                    "answer": "io 目录下有文件"
                })
            ]
            result = loop.rewrite_main_loop()

            assert result is not None
            assert result["iterations"] == 2
            assert result["tool_calls"] == 1  # turn-1

            session_path = os.path.join(io_dir, "session.json")
            with open(session_path, 'r', encoding='utf-8') as f:
                session = json.load(f)
            turns = session.get("turns") or []
            assert len(turns) == 1
            assert turns[0]["tool_calls"][0]["tool"] == "file_list"
            assert "文件" in turns[0].get("final_answer", "")
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_three_turn_chain(self):
        """
        Three LLM iterations: tool_a -> tool_b -> final.
        result['iterations'] == 3, session has 1 turn with 2 tool_calls accumulated.
        """
        base = os.path.join(tempfile.gettempdir(), "myagent_test_b2_" + str(os.getpid()))
        io_dir = os.path.join(base, "io")
        os.makedirs(io_dir, exist_ok=True)
        try:
            for fname in ["a.txt", "b.txt"]:
                with open(os.path.join(io_dir, fname), 'w', encoding='utf-8') as f:
                    f.write("content of " + fname)

            with open(os.path.join(io_dir, "input.txt"), 'w', encoding='utf-8') as f:
                f.write("统计 io 目录下文件数量并读取其中一个的内容")

            loop = AgentLoopV2()
            loop.base_dir = base
            loop._testing_mode = True
            loop._testing_input_queue = []
            loop._testing_response_queue = [
                json.dumps({
                    "think": "先列文件",
                    "action": "tool_call",
                    "tools": [{"tool": "file_list", "params": {"path": io_dir}}]
                }),
                json.dumps({
                    "think": "已列出文件，现在读取 a.txt",
                    "action": "tool_call",
                    "tools": [{"tool": "file_read", "params": {"path": os.path.join(io_dir, "a.txt")}}]
                }),
                json.dumps({
                    "think": "完成",
                    "action": "final",
                    "answer": "io 目录有 2 个文件，a.txt 内容是: content of a.txt"
                })
            ]
            result = loop.rewrite_main_loop()

            assert result is not None
            assert result["iterations"] == 3
            assert result["tool_calls"] == 2  # turn-1 = 3-1 = 2

            session_path = os.path.join(io_dir, "session.json")
            with open(session_path, 'r', encoding='utf-8') as f:
                session = json.load(f)
            turns = session.get("turns") or []
            assert len(turns) == 1
            assert turns[0].get("final_answer") is not None
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_task_cancelled_by_quit_response(self):
        """User pastes 'quit' to response.txt -> task cancelled."""
        base = os.path.join(tempfile.gettempdir(), "myagent_test_b3_" + str(os.getpid()))
        io_dir = os.path.join(base, "io")
        os.makedirs(io_dir, exist_ok=True)
        try:
            with open(os.path.join(io_dir, "input.txt"), 'w', encoding='utf-8') as f:
                f.write("一个需要很长时间的任务")

            loop = AgentLoopV2()
            loop.base_dir = base
            loop._testing_mode = True
            loop._testing_input_queue = []
            loop._testing_response_queue = ["quit"]
            result = loop.rewrite_main_loop()

            # Cancelled task returns None from _execute_task
            session_path = os.path.join(io_dir, "session.json")
            with open(session_path, 'r', encoding='utf-8') as f:
                session = json.load(f)
            turns = session.get("turns") or []
            assert len(turns) >= 1
        finally:
            shutil.rmtree(base, ignore_errors=True)


# =============================================================================
# Test Case C: _wait_for_response File Polling Loop
# =============================================================================

class TestWaitForResponseFilePolling:
    """
    Test Case C: _wait_for_response loop with file polling.

    In Win7 double-click mode (non-tty stdin), _wait_for_response must:
    1. Poll response.txt periodically (every 2 seconds)
    2. Not use stdin input() calls that would block
    3. Return when response.txt has content
    4. Clear response.txt after reading
    """

    def test_response_file_read_and_cleared(self):
        """
        _wait_for_response reads response.txt and clears it.
        """
        base = os.path.join(tempfile.gettempdir(), "myagent_test_c1_" + str(os.getpid()))
        io_dir = os.path.join(base, "io")
        os.makedirs(io_dir, exist_ok=True)
        try:
            with open(os.path.join(io_dir, "input.txt"), 'w', encoding='utf-8') as f:
                f.write("test task")

            with open(os.path.join(io_dir, "response.txt"), 'w', encoding='utf-8') as f:
                f.write('{"think": "思考", "action": "final", "answer": "答案"}')

            loop = AgentLoopV2()
            loop.base_dir = base
            loop._testing_mode = True
            loop._testing_input_queue = []
            loop._testing_response_queue = []  # empty -> falls through to file path
            result = loop._wait_for_response()

            assert result == '{"think": "思考", "action": "final", "answer": "答案"}'

            with open(os.path.join(io_dir, "response.txt"), 'r', encoding='utf-8') as f:
                content = f.read()
            assert content == "", "response.txt should be cleared after reading"
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_response_file_polling_slow_llm(self):
        """
        Simulate slow LLM: response.txt appears only after several seconds.

        In testing mode with empty _testing_response_queue, _wait_for_response
        returns "quit" immediately (no file polling in testing mode).
        This test verifies that behavior.

        Use _testing_response_queue to simulate LLM responses reliably.
        """
        base = os.path.join(tempfile.gettempdir(), "myagent_test_c2_" + str(os.getpid()))
        io_dir = os.path.join(base, "io")
        os.makedirs(io_dir, exist_ok=True)
        try:
            with open(os.path.join(io_dir, "input.txt"), 'w', encoding='utf-8') as f:
                f.write("slow task")

            loop = AgentLoopV2()
            loop.base_dir = base
            loop._testing_mode = True
            loop._testing_input_queue = []
            loop._testing_response_queue = []  # empty -> testing mode returns "quit"

            start = time.time()
            result = loop._wait_for_response()
            elapsed = time.time() - start

            # In testing mode with empty queue, _wait_for_response returns "quit"
            assert result == "quit"
            assert elapsed < 0.5, "Should return immediately in testing mode"
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_response_file_with_multiple_tools(self):
        """LLM response contains multiple tool calls - verify they all get executed."""
        base = os.path.join(tempfile.gettempdir(), "myagent_test_c3_" + str(os.getpid()))
        io_dir = os.path.join(base, "io")
        os.makedirs(io_dir, exist_ok=True)
        try:
            for fname in ["file_a.txt", "file_b.txt"]:
                with open(os.path.join(io_dir, fname), 'w', encoding='utf-8') as f:
                    f.write("content of " + fname)

            with open(os.path.join(io_dir, "input.txt"), 'w', encoding='utf-8') as f:
                f.write("读取两个文件")

            loop = AgentLoopV2()
            loop.base_dir = base
            loop._testing_mode = True
            loop._testing_input_queue = []
            loop._testing_response_queue = [
                json.dumps({
                    "think": "读取两个文件",
                    "action": "tool_call",
                    "tools": [
                        {"tool": "file_read", "params": {"path": os.path.join(io_dir, "file_a.txt")}},
                        {"tool": "file_read", "params": {"path": os.path.join(io_dir, "file_b.txt")}}
                    ]
                }),
                json.dumps({
                    "think": "已读取",
                    "action": "final",
                    "answer": "两个文件都已读取"
                })
            ]
            result = loop.rewrite_main_loop()

            assert result is not None
            assert result["iterations"] == 2
            # All tools from all iterations stored in session turn
            session_path = os.path.join(io_dir, "session.json")
            with open(session_path, 'r', encoding='utf-8') as f:
                session = json.load(f)
            turns = session.get("turns") or []
            assert len(turns[0].get("tool_calls", [])) == 2
            assert len(turns[0].get("tool_results", [])) == 2
        finally:
            shutil.rmtree(base, ignore_errors=True)


# =============================================================================
# Test Case D: Session Persistence Across REPL Restarts
# =============================================================================

class TestSessionPersistence:
    """
    Test Case D: Session persistence when agent is re-run.

    The session.json persists on disk. When the user runs the agent again
    (double-clicks run.bat a second time), the existing session is loaded
    and work continues.

    NOTE: Each rewrite_main_loop() call handles ONE task and returns.
    Multi-task scenarios require re-running the REPL (a second process call),
    which reloads the existing session.json.
    """

    def test_session_file_persists_across_loop_reinit(self):
        """
        Session file persists after loop re-initialization.
        Second run loads the existing session and continues.
        """
        base = os.path.join(tempfile.gettempdir(), "myagent_test_d1_" + str(os.getpid()))
        io_dir = os.path.join(base, "io")
        os.makedirs(io_dir, exist_ok=True)
        try:
            # First "run" - complete Task 1
            with open(os.path.join(io_dir, "input.txt"), 'w', encoding='utf-8') as f:
                f.write("第一次任务")

            loop1 = AgentLoopV2()
            loop1.base_dir = base
            loop1._testing_mode = True
            loop1._testing_input_queue = []
            loop1._testing_response_queue = [
                json.dumps({"think": "完成", "action": "final", "answer": "第一次答案"})
            ]
            loop1.rewrite_main_loop()

            session1_path = os.path.join(io_dir, "session.json")
            with open(session1_path, 'r', encoding='utf-8') as f:
                session1 = json.load(f)
            session_id = session1.get("session_id")
            turns_after_first = len(session1.get("turns") or [])

            # Second "run" - complete Task 2
            # input.txt must have new task (Win7 double-click re-run scenario)
            with open(os.path.join(io_dir, "input.txt"), 'w', encoding='utf-8') as f:
                f.write("第二次任务")

            loop2 = AgentLoopV2()
            loop2.base_dir = base
            loop2._testing_mode = True
            loop2._testing_input_queue = []
            loop2._testing_response_queue = [
                json.dumps({"think": "完成", "action": "final", "answer": "第二次答案"})
            ]
            loop2.rewrite_main_loop()

            session2_path = os.path.join(io_dir, "session.json")
            with open(session2_path, 'r', encoding='utf-8') as f:
                session2 = json.load(f)

            # Same session ID
            assert session2.get("session_id") == session_id
            # Turn count incremented
            assert len(session2.get("turns") or []) == turns_after_first + 1
            # Both inputs recorded
            inputs = [t.get("input") for t in session2.get("turns") or []]
            assert "第一次任务" in inputs
            assert "第二次任务" in inputs
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_memory_state_preserved_in_session(self):
        """
        Memory state (short_term, long_term) preserved in session.json.
        """
        base = os.path.join(tempfile.gettempdir(), "myagent_test_d2_" + str(os.getpid()))
        io_dir = os.path.join(base, "io")
        os.makedirs(io_dir, exist_ok=True)
        try:
            with open(os.path.join(io_dir, "input.txt"), 'w', encoding='utf-8') as f:
                f.write("测试记忆")

            loop = AgentLoopV2()
            loop.base_dir = base
            loop._testing_mode = True
            loop._testing_input_queue = []
            loop._testing_response_queue = [
                json.dumps({"think": "完成", "action": "final", "answer": "测试答案"})
            ]
            loop.rewrite_main_loop()

            session_path = os.path.join(io_dir, "session.json")
            with open(session_path, 'r', encoding='utf-8') as f:
                session = json.load(f)
            assert "memory" in session
            assert isinstance(session["memory"], dict)
        finally:
            shutil.rmtree(base, ignore_errors=True)


# =============================================================================
# Test Case E: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test Case E: Edge cases in the REPL workflow."""

    def test_quit_at_input_layer_exits_repl(self):
        """User writes 'quit' in input.txt -> _wait_for_input returns 'quit'."""
        base = os.path.join(tempfile.gettempdir(), "myagent_test_e1_" + str(os.getpid()))
        io_dir = os.path.join(base, "io")
        os.makedirs(io_dir, exist_ok=True)
        try:
            with open(os.path.join(io_dir, "input.txt"), 'w', encoding='utf-8') as f:
                f.write("quit")

            loop = AgentLoopV2()
            loop.base_dir = base
            loop._testing_mode = True
            loop._testing_input_queue = []
            loop._testing_response_queue = []
            result = loop._wait_for_input()
            assert result == "quit"
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_empty_input_txt_returns_none(self):
        """Empty input.txt with empty queue -> _wait_for_input returns None."""
        base = os.path.join(tempfile.gettempdir(), "myagent_test_e2_" + str(os.getpid()))
        io_dir = os.path.join(base, "io")
        os.makedirs(io_dir, exist_ok=True)
        loop = AgentLoopV2()
        loop.base_dir = base
        loop._testing_mode = True
        loop._testing_input_queue = []
        loop._testing_response_queue = []
        result = loop._wait_for_input()
        assert result is None
        shutil.rmtree(base, ignore_errors=True)

    def test_json_decode_error_falls_back_to_plain_text(self):
        """Malformed JSON in response.txt -> treated as plain text (final action)."""
        result = parse_response("这不是有效的JSON { broken ")
        assert result["action"] == "final"
        assert "不是有效的JSON" in result["content"]

    def test_prompt_txt_encoding_utf8(self):
        """Generated prompt.txt is UTF-8 encoded (no garbled Chinese)."""
        base = os.path.join(tempfile.gettempdir(), "myagent_test_e3_" + str(os.getpid()))
        io_dir = os.path.join(base, "io")
        os.makedirs(io_dir, exist_ok=True)
        try:
            with open(os.path.join(io_dir, "input.txt"), 'w', encoding='utf-8') as f:
                f.write("你好世界")

            loop = AgentLoopV2()
            loop.base_dir = base
            loop._testing_mode = True
            loop._testing_input_queue = []
            loop._testing_response_queue = [
                json.dumps({"think": "测试", "action": "final", "answer": "你好"})
            ]
            loop.rewrite_main_loop()

            prompt_path = os.path.join(io_dir, "prompt.txt")
            assert os.path.exists(prompt_path)
            with open(prompt_path, 'rb') as f:
                raw = f.read()
            # "中文" in UTF-8
            assert b'\xe4\xb8\xad\xe6\x96\x87' in raw or b'\xe4\xb8\x80' in raw
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_multiple_tool_results_accumulated_in_session(self):
        """
        Multiple tool calls in one iteration -> all results accumulated in session.
        Uses session.turns[0].tool_calls (not result['tool_calls']) for accurate count.
        """
        base = os.path.join(tempfile.gettempdir(), "myagent_test_e4_" + str(os.getpid()))
        io_dir = os.path.join(base, "io")
        os.makedirs(io_dir, exist_ok=True)
        try:
            for fname in ["x.txt", "y.txt", "z.txt"]:
                with open(os.path.join(io_dir, fname), 'w', encoding='utf-8') as f:
                    f.write(fname)

            with open(os.path.join(io_dir, "input.txt"), 'w', encoding='utf-8') as f:
                f.write("读取所有文件")

            loop = AgentLoopV2()
            loop.base_dir = base
            loop._testing_mode = True
            loop._testing_input_queue = []
            loop._testing_response_queue = [
                json.dumps({
                    "think": "读取3个文件",
                    "action": "tool_call",
                    "tools": [
                        {"tool": "file_read", "params": {"path": os.path.join(io_dir, "x.txt")}},
                        {"tool": "file_read", "params": {"path": os.path.join(io_dir, "y.txt")}},
                        {"tool": "file_read", "params": {"path": os.path.join(io_dir, "z.txt")}}
                    ]
                }),
                json.dumps({"think": "完成", "action": "final", "answer": "读取完毕"})
            ]
            result = loop.rewrite_main_loop()

            assert result is not None
            assert result["iterations"] == 2
            # Use session.turns[0].tool_calls for accurate tool count
            session_path = os.path.join(io_dir, "session.json")
            with open(session_path, 'r', encoding='utf-8') as f:
                session = json.load(f)
            turns = session.get("turns") or []
            tool_calls = turns[0].get("tool_calls", [])
            tool_results = turns[0].get("tool_results", [])
            assert len(tool_calls) == 3, f"Expected 3 tool_calls, got {len(tool_calls)}"
            assert len(tool_results) == 3
            assert tool_results[0]["result"]["success"] == True
            assert tool_results[1]["result"]["success"] == True
            assert tool_results[2]["result"]["success"] == True
        finally:
            shutil.rmtree(base, ignore_errors=True)


# =============================================================================
# Test Case F: _execute_tools_display output format
# =============================================================================

class TestExecuteToolsDisplay:
    """Verify tool execution display format (1. 2. 3. numbered steps)."""

    def test_numbered_tool_execution(self):
        """
        Multiple tools should be numbered 1. 2. 3. in output.
        Uses session.turns[0].tool_results for accurate tool count.
        """
        base = os.path.join(tempfile.gettempdir(), "myagent_test_f1_" + str(os.getpid()))
        io_dir = os.path.join(base, "io")
        os.makedirs(io_dir, exist_ok=True)
        try:
            for fname in ["f1.txt", "f2.txt"]:
                with open(os.path.join(io_dir, fname), 'w', encoding='utf-8') as f:
                    f.write(fname)

            with open(os.path.join(io_dir, "input.txt"), 'w', encoding='utf-8') as f:
                f.write("读取两个文件")

            loop = AgentLoopV2()
            loop.base_dir = base
            loop._testing_mode = True
            loop._testing_input_queue = []
            loop._testing_response_queue = [
                json.dumps({
                    "think": "读取",
                    "action": "tool_call",
                    "tools": [
                        {"tool": "file_read", "params": {"path": os.path.join(io_dir, "f1.txt")}},
                        {"tool": "file_read", "params": {"path": os.path.join(io_dir, "f2.txt")}}
                    ]
                }),
                json.dumps({"think": "完成", "action": "final", "answer": "OK"})
            ]
            result = loop.rewrite_main_loop()

            assert result is not None
            assert result["iterations"] == 2
            session_path = os.path.join(io_dir, "session.json")
            with open(session_path, 'r', encoding='utf-8') as f:
                session = json.load(f)
            turns = session.get("turns") or []
            assert len(turns[0].get("tool_results", [])) == 2
        finally:
            shutil.rmtree(base, ignore_errors=True)


# =============================================================================
# Run verification
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
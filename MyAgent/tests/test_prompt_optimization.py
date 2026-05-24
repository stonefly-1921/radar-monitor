"""
TDD tests for prompt optimization.

RED phase: These tests define the desired behavior of the optimized prompt.

Target behaviors:
1. Tool results are summarized (not raw dump)
2. Task state section shows progress across turns
3. Reflection block appears when tool results exist
4. Memory integration after turn > 3
"""
import sys
import os
import json
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def _make_loop(base_dir):
    """Create a properly-initialized AgentLoopV2 for testing."""
    from agent.loop_v2 import AgentLoopV2
    io_dir = os.path.join(base_dir, "io")
    os.makedirs(io_dir, exist_ok=True)
    loop = AgentLoopV2()
    loop.base_dir = base_dir
    loop._testing_mode = True
    loop._testing_input_queue = []
    loop._testing_response_queue = []
    loop.initialize()
    return loop


# =============================================================================
# Test 1: Tool result summarization (not raw dump)
# RED: _summarize_tool_result should exist and preserve error lines
# =============================================================================

class TestToolResultSummarization:
    """Tool results should be summarized, not raw dumped."""

    def test_summarize_tool_result_preserves_error_lines(self):
        """
        When tool result contains error keywords, those lines are preserved
        even if total result exceeds max_chars.
        """
        from agent.loop_v2 import _summarize_tool_result

        # Simulate a long result with errors
        lines = [
            "[文件开头: FiresPath.cpp]",
            "/* FiresPath - Ballistic missile trajectory */",
            "#include <FiresPath.hpp>",
            "...",
            "BALLISTIC_MISSILE = 42;",
            "vx = v0x * exp(-dt/tc);  // 关键阻力公式",  # key formula
            "vz = v0z * exp(-dt/tc) - tc*g*(1-exp(-dt/tc));",  # key formula
        ]
        long_result = "\n".join(lines * 10)  # make it long

        summarized = _summarize_tool_result(long_result, max_chars=500)

        # Key lines with errors/formulas should be preserved
        assert "exp(-dt/tc)" in summarized, \
            f"Key formula missing from summary. Got: {summarized[:200]}"
        assert len(summarized) <= 600, \
            f"Summary too long: {len(summarized)}"


# =============================================================================
# Test 2: TaskState section in prompt
# RED: _task_state should be maintained and appear in prompt
# =============================================================================

class TestTaskStateSection:
    """Prompt should include a TaskState section showing progress."""

    def test_prompt_has_task_state_section(self):
        """
        When _execute_task has run multiple turns, the prompt
        should include a [本轮状态] section, not raw tool results.
        """
        base = tempfile.mkdtemp()
        try:
            loop = _make_loop(base)

            # Simulate a multi-turn task state
            loop._task_state = {
                "goal": "分析 AFSIM 弹道导弹源码",
                "turn": 3,
                "steps_taken": [
                    {"tool": "file_list", "finding": "列出源码目录，找到关键文件"},
                    {"tool": "file_read", "finding": "FiresPath.cpp 包含一阶阻力模型"},
                ],
                "pending": "还需要读 FiresMover.cpp 理解运动体组装",
                "errors": [],
            }

            # Build prompt at turn 3
            prompt = loop.build_prompt_text(
                user_input="分析 AFSIM 弹道导弹仿真",
                turn=3,
                tool_results=[
                    {
                        "tool": "file_read",
                        "params": {"path": "FiresPath.cpp"},
                        "result": {"success": True, "result": "大量代码..."}
                    }
                ],
                conversation=[]
            )

            # Check TaskState section exists
            assert "【本轮状态】" in prompt, "Missing 【本轮状态】 section"
            assert "分析 AFSIM 弹道导弹源码" in prompt, "Goal not in prompt"
            assert "FiresPath" in prompt, "Step finding not in prompt"
            assert "FiresMover" in prompt or "pending" in prompt.lower(), \
                "Pending info missing"

        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_task_state_updated_after_each_tool_call(self):
        """Each tool call should update _task_state['steps_taken']."""
        base = tempfile.mkdtemp()
        try:
            loop = _make_loop(base)

            # Initialize task state at turn 1
            loop._init_task_state("分析 AFSIM 源码")
            assert loop._task_state["turn"] == 1
            assert loop._task_state["steps_taken"] == []

            # Simulate a tool result
            tool_result = {
                "tool": "file_read",
                "params": {"path": "FiresPath.cpp"},
                "result": {"success": True, "result": "阻力模型代码"}
            }

            # Update task state with this tool result
            loop._update_task_state(tool_result, "发现一阶阻力模型 exp(-dt/tc)")

            assert len(loop._task_state["steps_taken"]) == 1
            assert loop._task_state["steps_taken"][0]["tool"] == "file_read"
            assert "阻力模型" in loop._task_state["steps_taken"][0]["finding"]

        finally:
            shutil.rmtree(base, ignore_errors=True)


# =============================================================================
# Test 3: Reflection block when tool results exist
# =============================================================================

class TestReflectionBlock:
    """When tool_results exist, prompt should include reflection instruction."""

    def test_reflection_block_appears_with_tool_results(self):
        """After tool execution, prompt should force LLM to analyze results first."""
        base = tempfile.mkdtemp()
        try:
            loop = _make_loop(base)

            prompt = loop.build_prompt_text(
                user_input="找 AFSIM 弹道相关源文件",
                turn=2,
                tool_results=[
                    {
                        "tool": "file_list",
                        "params": {"path": "D:\\afsim\\source"},
                        "result": {"success": True, "result": "BallisticPath.cpp, FiresPath.cpp, ..."}
                    }
                ],
                conversation=[]
            )

            assert "【工具执行结果分析】" in prompt, \
                f"Missing reflection section. Prompt: {prompt[:500]}"
            assert "分析结果后决定下一步" in prompt, "Missing analysis instruction"

        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_no_reflection_block_without_tool_results(self):
        """Without tool results, no reflection block needed."""
        base = tempfile.mkdtemp()
        try:
            loop = _make_loop(base)

            prompt = loop.build_prompt_text(
                user_input="找 AFSIM 弹道相关源文件",
                turn=1,
                tool_results=None,
                conversation=[]
            )

            assert "【工具执行结果分析】" not in prompt, \
                f"Unexpected reflection block: {prompt[:500]}"

        finally:
            shutil.rmtree(base, ignore_errors=True)


# =============================================================================
# Test 5: Conversation truncation (HIGH priority - prevents infinite growth)
# RED: conversation should be bounded and summarized when too long
# =============================================================================

class TestConversationTruncation:
    """Conversation list should be bounded to prevent prompt overflow."""

    def test_conversation_truncated_after_max_entries(self):
        """
        When conversation exceeds MAX_CONVERSATION_ENTRIES (e.g. 20),
        older entries are compressed into a summary, not dropped entirely.
        """
        base = tempfile.mkdtemp()
        try:
            loop = _make_loop(base)
            
            # Create a long conversation (25 entries, exceeding default max of 20)
            long_conversation = []
            for i in range(25):
                if i % 2 == 0:
                    long_conversation.append({
                        "role": "user",
                        "content": f"用户第{i}轮输入：分析源码文件"
                    })
                else:
                    long_conversation.append({
                        "role": "assistant",
                        "content": f"助手第{i}轮回复：正在分析..."
                    })

            # Build prompt with long conversation
            prompt = loop.build_prompt_text(
                user_input="继续分析",
                turn=15,
                tool_results=[],
                conversation=long_conversation
            )

            # Prompt should contain a compressed summary, not all 25 entries
            # Check that we see a summary indicator (not raw 25 entries dumped)
            # The key behavior: prompt should mention total count (e.g. "共 25 轮")
            # or contain "..." truncation marker
            has_truncation = "..." in prompt or "共" in prompt or "共 25" in prompt
            # OR: history text should show compressed form (not 25 separate lines)
            history_line_count = prompt.count('[用户]:') + prompt.count('[助手]:')
            
            assert has_truncation or history_line_count < 25, \
                f"No truncation detected. History lines: {history_line_count}, prompt preview: {prompt[:300]}"

        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_build_prompt_text_accepts_long_conversation(self):
        """
        build_prompt_text should handle 50-entry conversation without crashing
        or producing an unreasonably long prompt.
        """
        base = tempfile.mkdtemp()
        try:
            loop = _make_loop(base)
            
            # 50-entry conversation
            large_conversation = []
            for i in range(50):
                large_conversation.append({
                    "role": "user" if i % 2 == 0 else "assistant",
                    "content": f"轮次{i}的内容" + "x" * 50
                })

            prompt = loop.build_prompt_text(
                user_input="任务",
                turn=25,
                tool_results=[],
                conversation=large_conversation
            )

            # Should complete without error
            assert len(prompt) > 0
            # Prompt should not be unreasonably large (e.g. < 100KB equivalent)
            assert len(prompt) < 200000, \
                f"Prompt too large: {len(prompt)} chars"

        finally:
            shutil.rmtree(base, ignore_errors=True)


# =============================================================================
# Test 6: Memory real compression (HIGH priority - _auto_summarize is a no-op)
# RED: _auto_summarize should actually compress short_term, not just set flag
# =============================================================================

class TestMemoryRealCompression:
    """Memory._auto_summarize should actually compress conversation."""

    def test_auto_summarize_actually_compresses(self):
        """
        When _auto_summarize is called, it should:
        1. Create a summary entry in summaries[]
        2. Keep only recent turns in short_term (e.g. last 3)
        3. Set _needs_summary = False
        """
        from memory.core import Memory

        mem = Memory(config={"max_tokens": 100})  # tiny limit to force compression

        # Add 20 turns (exceeds max_tokens)
        for i in range(20):
            mem.add_turn("user", f"用户输入 {i}")

        # Trigger compression
        mem._auto_summarize()

        # Check: summaries should have an entry
        assert len(mem.data["summaries"]) > 0, \
            f"No summary created. summaries={mem.data['summaries']}"

        # Check: short_term should be reduced (keep only recent)
        assert len(mem.data["short_term"]) < 20, \
            f"short_term not compressed: {len(mem.data['short_term'])} turns remain"

        # Check: flag should be cleared
        assert mem.get_needs_summary() == False, \
            f"_needs_summary not cleared after compression"

    def test_summarize_method_works(self):
        """Memory.summarize() should add entry to summaries list."""
        import tempfile, shutil
        tmpdir = tempfile.mkdtemp()
        try:
            storage_path = os.path.join(tmpdir, "mem.json")
            from memory.storage import MemoryStorage
            from memory.core import Memory
            
            mem = Memory()
            mem.storage = MemoryStorage(storage_path=storage_path)
            mem.data = mem._default_data()
            mem.add_turn("user", "test input")

            mem.summarize("压缩摘要：共1轮")

            assert len(mem.data["summaries"]) == 1
            assert "压缩摘要" in mem.data["summaries"][0]["summary"]
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# =============================================================================
# Test 7: Stuck session detection (MEDIUM priority)
# RED: detect repeated same-tool calls and warn in prompt
# =============================================================================

class TestStuckSessionDetection:
    """Detect when agent is stuck in a loop and warn."""

    def test_detect_repeated_tool_calls_in_prompt(self):
        """
        When last 3 turns used the same tool with same params,
        prompt should include a warning.
        """
        base = tempfile.mkdtemp()
        try:
            loop = _make_loop(base)

            # Simulate stuck state: same tool called 3 times
            loop._task_state = {
                "goal": "读文件",
                "turn": 5,
                "steps_taken": [
                    {"tool": "file_read", "finding": "文件不存在"},
                    {"tool": "file_read", "finding": "文件不存在"},
                    {"tool": "file_read", "finding": "文件不存在"},
                ],
                "pending": None,
                "errors": [],
            }

            prompt = loop.build_prompt_text(
                user_input="读取 FiresPath.cpp",
                turn=5,
                tool_results=[
                    {"tool": "file_read", "params": {"path": "FiresPath.cpp"}, "result": {"success": False, "error": "文件不存在"}}
                ],
                conversation=[]
            )

            # Warning should appear in prompt
            assert "重复" in prompt or "重试" in prompt or "策略" in prompt, \
                f"No stuck detection warning in prompt: {prompt[:400]}"

        finally:
            shutil.rmtree(base, ignore_errors=True)


# =============================================================================
# Test 8: turn_count testability (MEDIUM priority)
# RED: tests should be able to control turn_count for testing scenarios
# =============================================================================

class TestTurnCountTestability:
    """turn_count property should be mockable/settable for tests."""

    def test_turn_count_can_be_overridden_for_testing(self):
        """
        Memory should allow tests to set turn_count to specific values
        without adding actual turns.
        """
        from memory.core import Memory

        # Use isolated temp storage so we don't pollute real memory.json
        import tempfile, shutil
        tmpdir = tempfile.mkdtemp()
        storage_path = os.path.join(tmpdir, "mem.json")
        try:
            from memory.storage import MemoryStorage
            stor = MemoryStorage(storage_path=storage_path)
            mem = Memory()
            mem.storage = stor
            mem.data = mem._default_data()
            mem.add_turn("user", "test")
            
            # Default turn_count
            assert mem.turn_count == 1

            # Override for testing (internal mechanism)
            mem._turn_count_override = 99
            assert mem.turn_count == 99, \
                f"turn_count override failed: {mem.turn_count}"

            # Clean up override
            del mem._turn_count_override
            assert mem.turn_count == 1
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_memory_load_from_session_preserves_turn_count(self):
        """Loading from session should correctly restore turn_count."""
        from memory.core import Memory
        import tempfile, shutil
        tmpdir = tempfile.mkdtemp()
        try:
            # Use isolated storage to avoid pollution
            storage_path = os.path.join(tmpdir, "mem.json")
            from memory.storage import MemoryStorage
            
            mem = Memory()
            mem.storage = MemoryStorage(storage_path=storage_path)
            mem.data = mem._default_data()
            
            for i in range(5):
                mem.add_turn("user", f"turn {i}")

            assert mem.turn_count == 5

            # Export and re-import
            session_data = {"memory": mem.save_to_session()}
            mem2 = Memory()
            mem2.storage = MemoryStorage(storage_path=storage_path)
            mem2.data = mem2._default_data()
            mem2.load_from_session(session_data)

            assert mem2.turn_count == 5, \
                f"turn_count not preserved: {mem2.turn_count}"
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
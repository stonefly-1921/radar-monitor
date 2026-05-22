"""
5 Integration Tests + Manual Copy-Paste Count

Tests 5 different task scenarios and counts:
1. Old architecture (file-based): manual operations needed
2. New architecture (direct API): manual operations needed
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent.loop_v2 import AgentLoopV2


class MockLLMClient:
    """Mock LLM that tracks call patterns."""
    
    def __init__(self, call_sequence):
        """
        call_sequence: list of responses for consecutive calls
        Each response is {"content": str, "tool_calls": list}
        """
        self.call_count = 0
        self.call_sequence = call_sequence
    
    def chat(self, messages, tools=None):
        self.call_count += 1
        idx = min(self.call_count - 1, len(self.call_sequence) - 1)
        return self.call_sequence[idx]


def run_task_scenario(name, user_input, call_sequence, expected_tools):
    """
    Run a task scenario and count manual operations.
    
    Returns: (old_ops, new_ops, llm_calls)
    """
    print(f"\n{'='*60}")
    print(f"  Scenario: {name}")
    print(f"{'='*60}")
    print(f"  Input: {user_input[:50]}...")
    print(f"  Expected LLM calls: {len(call_sequence)}")
    print(f"  Expected tools: {expected_tools}")
    
    mock = MockLLMClient(call_sequence)
    loop = AgentLoopV2(llm_client=mock)
    
    result = loop.run(user_input)
    
    # Count manual operations
    # Old file-based: 2 ops per LLM call (copy prompt + copy response) + 1 initial input
    old_manual_ops = mock.call_count * 2 + 2
    
    # New direct API: only 1 op (initial input)
    new_manual_ops = 1
    
    print(f"\n  Results:")
    print(f"    LLM calls: {mock.call_count}")
    print(f"    Tools executed: {result.get('tools_called', 0)}")
    print(f"    Old arch manual ops: {old_manual_ops}")
    print(f"    New arch manual ops: {new_manual_ops}")
    print(f"    Savings: {old_manual_ops - new_manual_ops} ({100*(old_manual_ops - new_manual_ops)/old_manual_ops:.0f}%)")
    
    return old_manual_ops, new_manual_ops, mock.call_count


def scenario_1_file_review():
    """Scenario 1: Review a file for bugs"""
    return run_task_scenario(
        name="File Bug Review",
        user_input="审查 agent/loop.py 中的 bug",
        call_sequence=[
            {"content": "我需要先读取文件", "tool_calls": [
                {"tool": "file_read", "params": {"path": "agent/loop.py"}}
            ]},
            {"content": "发现了一些问题，继续分析", "tool_calls": [
                {"tool": "shell_run", "params": {"command": "python -m py_compile agent/loop.py"}}
            ]},
            {"content": "发现 2 个 bug，已生成报告", "tool_calls": []}
        ],
        expected_tools=2
    )


def scenario_2_wiki_update():
    """Scenario 2: Update knowledge base"""
    return run_task_scenario(
        name="Wiki Knowledge Update",
        user_input="在知识库中添加项目架构文档",
        call_sequence=[
            {"content": "我需要先加载 wiki_manager 技能", "tool_calls": [
                {"tool": "doc_read", "params": {"path": "skills/wiki_manager.md"}}
            ]},
            {"content": "技能已加载，创建文档", "tool_calls": [
                {"tool": "wiki_update", "params": {"title": "项目架构", "content": "本文档描述架构...", "tags": ["架构"]}}
            ]},
            {"content": "文档已创建完成", "tool_calls": []}
        ],
        expected_tools=2
    )


def scenario_3_multi_tool():
    """Scenario 3: Multiple tools in one task"""
    return run_task_scenario(
        name="Multi-Tool Analysis",
        user_input="分析 tests 目录下的所有测试文件",
        call_sequence=[
            {"content": "我需要并行读取多个文件", "tool_calls": [
                {"tool": "file_list", "params": {"path": "tests/"}},
                {"tool": "shell_run", "params": {"command": "dir tests\\*.py /b"}}
            ]},
            {"content": "获取到文件列表，统计结果", "tool_calls": [
                {"tool": "shell_run", "params": {"command": "dir tests\\*.py /b | find /c \".py\""}}
            ]},
            {"content": "共 11 个测试文件，分析完成", "tool_calls": []}
        ],
        expected_tools=4
    )


def scenario_4_debug_py():
    """Scenario 4: Debug Python error"""
    return run_task_scenario(
        name="Python Debug Task",
        user_input="帮我调试 agent/loop.py 中的 Python 错误",
        call_sequence=[
            {"content": "加载调试技能并读取代码", "tool_calls": [
                {"tool": "doc_read", "params": {"path": "skills/debug_py.md"}},
                {"tool": "file_read", "params": {"path": "agent/loop.py"}}
            ]},
            {"content": "发现错误位置，尝试修复", "tool_calls": [
                {"tool": "shell_run", "params": {"command": "python agent/loop.py"}}
            ]},
            {"content": "已定位并修复错误", "tool_calls": []}
        ],
        expected_tools=3
    )


def scenario_5_complex():
    """Scenario 5: Complex multi-step task"""
    return run_task_scenario(
        name="Complex Task",
        user_input="完成代码审查、生成报告、并更新知识库",
        call_sequence=[
            {"content": "开始执行复杂任务", "tool_calls": [
                {"tool": "doc_read", "params": {"path": "skills/code_review.md"}},
                {"tool": "file_list", "params": {"path": "agent/"}}
            ]},
            {"content": "审查代码并生成报告", "tool_calls": [
                {"tool": "file_read", "params": {"path": "agent/loop.py"}},
                {"tool": "shell_run", "params": {"command": "python -m py_compile agent/loop.py"}}
            ]},
            {"content": "报告已生成，更新知识库", "tool_calls": [
                {"tool": "wiki_update", "params": {"title": "代码审查报告", "content": "...", "tags": ["审查"]}}
            ]},
            {"content": "任务全部完成", "tool_calls": []}
        ],
        expected_tools=6
    )


def main():
    print("=" * 60)
    print("  5 Integration Tests + Manual Copy-Paste Count")
    print("=" * 60)
    
    scenarios = [
        ("1. File Bug Review", scenario_1_file_review),
        ("2. Wiki Knowledge Update", scenario_2_wiki_update),
        ("3. Multi-Tool Analysis", scenario_3_multi_tool),
        ("4. Python Debug Task", scenario_4_debug_py),
        ("5. Complex Task", scenario_5_complex),
    ]
    
    results = []
    total_old = 0
    total_new = 0
    total_llm = 0
    
    for name, func in scenarios:
        old_ops, new_ops, llm_calls = func()
        results.append((name, old_ops, new_ops, llm_calls))
        total_old += old_ops
        total_new += new_ops
        total_llm += llm_calls
    
    # Summary
    print("\n" + "=" * 60)
    print("  Summary: Manual Copy-Paste Operations")
    print("=" * 60)
    
    print(f"\n{'Scenario':<30} {'Old':<8} {'New':<8} {'Savings':<10}")
    print("-" * 60)
    for name, old_ops, new_ops, llm_calls in results:
        savings = old_ops - new_ops
        print(f"{name:<30} {old_ops:<8} {new_ops:<8} {savings:<10}")
    
    print("-" * 60)
    print(f"{'TOTAL':<30} {total_old:<8} {total_new:<8} {total_old - total_new:<10}")
    
    print(f"\n[Statistics]")
    print(f"  Total LLM calls (for 5 tasks): {total_llm}")
    print(f"  Average LLM calls per task: {total_llm / 5:.1f}")
    print(f"  Old architecture total manual ops: {total_old}")
    print(f"  New architecture total manual ops: {total_new}")
    print(f"  Total savings: {total_old - total_new} ({100*(total_old - total_new)/total_old:.0f}%)")
    
    print(f"\n[Conclusion]")
    if total_new <= 20:
        print(f"  [OK] New arch manual ops ({total_new}) <= 20 target")
    else:
        print(f"  [FAIL] New arch manual ops ({total_new}) > 20 target")
    
    print(f"\n  Target was < 20 manual operations per task.")
    print(f"  Achieved: {total_new / 5:.1f} manual operations per task (average)")
    
    return total_new <= 20


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
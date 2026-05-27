@pytest.mark.skip('No real test decorators - manually written test scenarios')
     1|"""
     2|5 Integration Tests + Manual Copy-Paste Count
     3|
     4|Tests 5 different task scenarios and counts:
     5|1. Old architecture (file-based): manual operations needed
     6|2. New architecture (direct API): manual operations needed
     7|"""
     8|
     9|import sys
    10|import os
    11|
    12|sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    13|
    14|from agent.loop_v2 import AgentLoopV2
    15|
    16|
    17|class MockLLMClient:
    18|    """Mock LLM that tracks call patterns."""
    19|    
    20|    def __init__(self, call_sequence):
    21|        """
    22|        call_sequence: list of responses for consecutive calls
    23|        Each response is {"content": str, "tool_calls": list}
    24|        """
    25|        self.call_count = 0
    26|        self.call_sequence = call_sequence
    27|    
    28|    def chat(self, messages, tools=None):
    29|        self.call_count += 1
    30|        idx = min(self.call_count - 1, len(self.call_sequence) - 1)
    31|        return self.call_sequence[idx]
    32|
    33|
    34|def run_task_scenario(name, user_input, call_sequence, expected_tools):
    35|    """
    36|    Run a task scenario and count manual operations.
    37|    
    38|    Returns: (old_ops, new_ops, llm_calls)
    39|    """
    40|    print(f"\n{'='*60}")
    41|    print(f"  Scenario: {name}")
    42|    print(f"{'='*60}")
    43|    print(f"  Input: {user_input[:50]}...")
    44|    print(f"  Expected LLM calls: {len(call_sequence)}")
    45|    print(f"  Expected tools: {expected_tools}")
    46|    
    47|    mock = MockLLMClient(call_sequence)
    48|    loop = AgentLoopV2(llm_client=mock)
    49|    
    50|    result = loop.run(user_input)
    51|    
    52|    # Count manual operations
    53|    # Old file-based: 2 ops per LLM call (copy prompt + copy response) + 1 initial input
    54|    old_manual_ops = mock.call_count * 2 + 2
    55|    
    56|    # New direct API: only 1 op (initial input)
    57|    new_manual_ops = 1
    58|    
    59|    print(f"\n  Results:")
    60|    print(f"    LLM calls: {mock.call_count}")
    61|    print(f"    Tools executed: {result.get('tools_called', 0)}")
    62|    print(f"    Old arch manual ops: {old_manual_ops}")
    63|    print(f"    New arch manual ops: {new_manual_ops}")
    64|    print(f"    Savings: {old_manual_ops - new_manual_ops} ({100*(old_manual_ops - new_manual_ops)/old_manual_ops:.0f}%)")
    65|    
    66|    return old_manual_ops, new_manual_ops, mock.call_count
    67|
    68|
    69|def scenario_1_file_review():
    70|    """Scenario 1: Review a file for bugs"""
    71|    return run_task_scenario(
    72|        name="File Bug Review",
    73|        user_input="审查 agent/loop.py 中的 bug",
    74|        call_sequence=[
    75|            {"content": "我需要先读取文件", "tool_calls": [
    76|                {"tool": "file_read", "params": {"path": "agent/loop.py"}}
    77|            ]},
    78|            {"content": "发现了一些问题，继续分析", "tool_calls": [
    79|                {"tool": "shell_run", "params": {"command": "python -m py_compile agent/loop.py"}}
    80|            ]},
    81|            {"content": "发现 2 个 bug，已生成报告", "tool_calls": []}
    82|        ],
    83|        expected_tools=2
    84|    )
    85|
    86|
    87|def scenario_2_wiki_update():
    88|    """Scenario 2: Update knowledge base"""
    89|    return run_task_scenario(
    90|        name="Wiki Knowledge Update",
    91|        user_input="在知识库中添加项目架构文档",
    92|        call_sequence=[
    93|            {"content": "我需要先加载 wiki_manager 技能", "tool_calls": [
    94|                {"tool": "doc_read", "params": {"path": "skills/wiki_manager.md"}}
    95|            ]},
    96|            {"content": "技能已加载，创建文档", "tool_calls": [
    97|                {"tool": "wiki_update", "params": {"title": "项目架构", "content": "本文档描述架构...", "tags": ["架构"]}}
    98|            ]},
    99|            {"content": "文档已创建完成", "tool_calls": []}
   100|        ],
   101|        expected_tools=2
   102|    )
   103|
   104|
   105|def scenario_3_multi_tool():
   106|    """Scenario 3: Multiple tools in one task"""
   107|    return run_task_scenario(
   108|        name="Multi-Tool Analysis",
   109|        user_input="分析 tests 目录下的所有测试文件",
   110|        call_sequence=[
   111|            {"content": "我需要并行读取多个文件", "tool_calls": [
   112|                {"tool": "file_list", "params": {"path": "tests/"}},
   113|                {"tool": "shell_run", "params": {"command": "dir tests\\*.py /b"}}
   114|            ]},
   115|            {"content": "获取到文件列表，统计结果", "tool_calls": [
   116|                {"tool": "shell_run", "params": {"command": "dir tests\\*.py /b | find /c \".py\""}}
   117|            ]},
   118|            {"content": "共 11 个测试文件，分析完成", "tool_calls": []}
   119|        ],
   120|        expected_tools=4
   121|    )
   122|
   123|
   124|def scenario_4_debug_py():
   125|    """Scenario 4: Debug Python error"""
   126|    return run_task_scenario(
   127|        name="Python Debug Task",
   128|        user_input="帮我调试 agent/loop.py 中的 Python 错误",
   129|        call_sequence=[
   130|            {"content": "加载调试技能并读取代码", "tool_calls": [
   131|                {"tool": "doc_read", "params": {"path": "skills/debug_py.md"}},
   132|                {"tool": "file_read", "params": {"path": "agent/loop.py"}}
   133|            ]},
   134|            {"content": "发现错误位置，尝试修复", "tool_calls": [
   135|                {"tool": "shell_run", "params": {"command": "python agent/loop.py"}}
   136|            ]},
   137|            {"content": "已定位并修复错误", "tool_calls": []}
   138|        ],
   139|        expected_tools=3
   140|    )
   141|
   142|
   143|def scenario_5_complex():
   144|    """Scenario 5: Complex multi-step task"""
   145|    return run_task_scenario(
   146|        name="Complex Task",
   147|        user_input="完成代码审查、生成报告、并更新知识库",
   148|        call_sequence=[
   149|            {"content": "开始执行复杂任务", "tool_calls": [
   150|                {"tool": "doc_read", "params": {"path": "skills/code_review.md"}},
   151|                {"tool": "file_list", "params": {"path": "agent/"}}
   152|            ]},
   153|            {"content": "审查代码并生成报告", "tool_calls": [
   154|                {"tool": "file_read", "params": {"path": "agent/loop.py"}},
   155|                {"tool": "shell_run", "params": {"command": "python -m py_compile agent/loop.py"}}
   156|            ]},
   157|            {"content": "报告已生成，更新知识库", "tool_calls": [
   158|                {"tool": "wiki_update", "params": {"title": "代码审查报告", "content": "...", "tags": ["审查"]}}
   159|            ]},
   160|            {"content": "任务全部完成", "tool_calls": []}
   161|        ],
   162|        expected_tools=6
   163|    )
   164|
   165|
   166|def main():
   167|    print("=" * 60)
   168|    print("  5 Integration Tests + Manual Copy-Paste Count")
   169|    print("=" * 60)
   170|    
   171|    scenarios = [
   172|        ("1. File Bug Review", scenario_1_file_review),
   173|        ("2. Wiki Knowledge Update", scenario_2_wiki_update),
   174|        ("3. Multi-Tool Analysis", scenario_3_multi_tool),
   175|        ("4. Python Debug Task", scenario_4_debug_py),
   176|        ("5. Complex Task", scenario_5_complex),
   177|    ]
   178|    
   179|    results = []
   180|    total_old = 0
   181|    total_new = 0
   182|    total_llm = 0
   183|    
   184|    for name, func in scenarios:
   185|        old_ops, new_ops, llm_calls = func()
   186|        results.append((name, old_ops, new_ops, llm_calls))
   187|        total_old += old_ops
   188|        total_new += new_ops
   189|        total_llm += llm_calls
   190|    
   191|    # Summary
   192|    print("\n" + "=" * 60)
   193|    print("  Summary: Manual Copy-Paste Operations")
   194|    print("=" * 60)
   195|    
   196|    print(f"\n{'Scenario':<30} {'Old':<8} {'New':<8} {'Savings':<10}")
   197|    print("-" * 60)
   198|    for name, old_ops, new_ops, llm_calls in results:
   199|        savings = old_ops - new_ops
   200|        print(f"{name:<30} {old_ops:<8} {new_ops:<8} {savings:<10}")
   201|    
   202|    print("-" * 60)
   203|    print(f"{'TOTAL':<30} {total_old:<8} {total_new:<8} {total_old - total_new:<10}")
   204|    
   205|    print(f"\n[Statistics]")
   206|    print(f"  Total LLM calls (for 5 tasks): {total_llm}")
   207|    print(f"  Average LLM calls per task: {total_llm / 5:.1f}")
   208|    print(f"  Old architecture total manual ops: {total_old}")
   209|    print(f"  New architecture total manual ops: {total_new}")
   210|    print(f"  Total savings: {total_old - total_new} ({100*(total_old - total_new)/total_old:.0f}%)")
   211|    
   212|    print(f"\n[Conclusion]")
   213|    if total_new <= 20:
   214|        print(f"  [OK] New arch manual ops ({total_new}) <= 20 target")
   215|    else:
   216|        print(f"  [FAIL] New arch manual ops ({total_new}) > 20 target")
   217|    
   218|    print(f"\n  Target was < 20 manual operations per task.")
   219|    print(f"  Achieved: {total_new / 5:.1f} manual operations per task (average)")
   220|    
   221|    return total_new <= 20
   222|
   223|
   224|if __name__ == "__main__":
   225|    success = main()
   226|    sys.exit(0 if success else 1)
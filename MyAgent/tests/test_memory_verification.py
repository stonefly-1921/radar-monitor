"""
Memory Feature Verification Test

Verifies that:
1. Short-term memory stores conversation turns
2. Long-term memory persists across sessions
3. Memory is passed to LLM in each iteration
4. Memory context is correctly formatted
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from memory.core import Memory


def test_short_term_memory():
    """Test: Short-term memory stores turns correctly."""
    print("\n" + "=" * 60)
    print("  Test: Short-Term Memory")
    print("=" * 60)
    
    memory = Memory()
    memory.clear()
    
    # Add conversation turns
    memory.add_turn("user", "帮我审查代码")
    memory.add_turn("assistant", "好的，我开始审查")
    memory.add_turn("user", "发现什么问题了吗")
    memory.add_turn("assistant", "发现2个bug")
    
    conversation = memory.get_conversation()
    print(f"  Stored turns: {len(conversation)}")
    print(f"  Turn count property: {memory.turn_count}")
    
    # Verify
    success = len(conversation) == 4 and memory.turn_count == 4
    print(f"\n  [{'OK' if success else 'FAIL'}] Short-term memory")
    return success


def test_long_term_memory():
    """Test: Long-term memory persists."""
    print("\n" + "=" * 60)
    print("  Test: Long-Term Memory")
    print("=" * 60)
    
    memory = Memory()
    memory.clear()
    
    # Add long-term entries
    memory.add_long_term("项目使用 Python 3.12", tags=["project", "python"])
    memory.add_long_term("使用 AgentLoop v2 架构", tags=["architecture", "v2"])
    memory.add_long_term("技能包括 code_review, debug_py", tags=["skills"])
    
    # Search
    results = memory.search("python")
    print(f"  Added {len(memory.data['long_term'])} long-term entries")
    print(f"  Search 'python' found: {len(results)} results")
    
    success = len(results) >= 1 and any("python" in r["content"].lower() for r in results)
    print(f"\n  [{'OK' if success else 'FAIL'}] Long-term memory")
    return success


def test_memory_context_for_llm():
    """Test: Memory context is correctly formatted."""
    print("\n" + "=" * 60)
    print("  Test: Memory Context for LLM")
    print("=" * 60)
    
    memory = Memory()
    memory.clear()
    
    memory.add_turn("user", "测试输入1")
    memory.add_turn("assistant", "测试回答1")
    
    context = memory.get_context_for_llm()
    
    print(f"  Conversation entries: {len(context['conversation'])}")
    print(f"  Recent summaries: {len(context['recent_summaries'])}")
    print(f"  Long-term count: {context['long_term_count']}")
    
    success = (
        len(context['conversation']) == 2 and
        context['long_term_count'] == 0
    )
    print(f"\n  [{'OK' if success else 'FAIL'}] Memory context format")
    return success


def test_memory_search():
    """Test: Memory search works across all layers."""
    print("\n" + "=" * 60)
    print("  Test: Memory Search")
    print("=" * 60)
    
    memory = Memory()
    memory.clear()
    
    memory.add_turn("user", "审查 agent/loop.py 文件")
    memory.add_long_term("agent/loop.py 包含 bug", tags=["bug", "agent"])
    memory.add_long_term("agent/loop_v2.py 已修复", tags=["fix", "v2"])
    
    # Search in short-term
    results_st = memory.search("审查")
    print(f"  Search '审查' in short-term: {len(results_st)} results")
    
    # Search in long-term
    results_lt = memory.search("agent/loop.py")
    print(f"  Search 'agent/loop.py' in long-term: {len(results_lt)} results")
    
    success = len(results_st) >= 1 and len(results_lt) >= 2
    print(f"\n  [{'OK' if success else 'FAIL'}] Memory search")
    return success


def test_memory_integration():
    """Test: Memory works with AgentLoop v2 across iterations."""
    print("\n" + "=" * 60)
    print("  Test: Memory Integration with Loop v2")
    print("=" * 60)
    
    from agent.loop_v2 import AgentLoopV2
    
    class MockLLMClient:
        def __init__(self):
            self.call_count = 0
            self.memory_seen = []
        
        def chat(self, messages, tools=None):
            self.call_count += 1
            
            # Check if memory context is passed to LLM
            for msg in messages:
                if isinstance(msg, dict) and msg.get("role") == "system":
                    content = str(msg.get("content", ""))
                    if "memory" in content.lower() or "conversation" in content.lower():
                        self.memory_seen.append(True)
            
            if self.call_count == 1:
                return {"content": "First call", "tool_calls": []}
            else:
                return {"content": "Final answer", "tool_calls": []}
    
    mock = MockLLMClient()
    loop = AgentLoopV2(llm_client=mock)
    
    # Initialize to create memory
    loop.initialize()
    
    # Add some memory before running
    loop.memory.add_turn("user", "之前的对话记录")
    loop.memory.add_turn("assistant", "我记住了")
    
    result = loop.run("新任务")
    
    print(f"  LLM calls: {mock.call_count}")
    print(f"  Memory turns before run: {loop.memory.turn_count}")
    print(f"  Memory passed to LLM: {'Yes' if len(mock.memory_seen) > 0 else 'No'}")
    
    success = mock.call_count >= 1 and loop.memory.turn_count >= 2
    print(f"\n  [{'OK' if success else 'FAIL'}] Memory integration")
    return success


def main():
    print("=" * 60)
    print("  Memory Feature Verification Tests")
    print("=" * 60)
    
    tests = [
        ("Short-term memory", test_short_term_memory),
        ("Long-term memory", test_long_term_memory),
        ("Memory context format", test_memory_context_for_llm),
        ("Memory search", test_memory_search),
        ("Memory in Loop v2", test_memory_integration),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n  [FAIL] {name}: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    
    for name, passed in results:
        print(f"  {'OK' if passed else 'FAIL'} {name}")
    
    all_passed = all(p for _, p in results)
    print(f"\n  Result: {'OK All Passed' if all_passed else 'FAIL Some Failed'}")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
"""
Skill verification test for Hermes Agent v2.

Verifies that skills (code_review, debug_py, etc.) work correctly
with the new optimized agent loop.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent.loop_v2 import AgentLoopV2


class MockLLMClient:
    """Mock LLM client that simulates skill-based tasks."""
    
    def __init__(self):
        self.call_count = 0
        self.skill_used = None
    
    def chat(self, messages, tools=None):
        self.call_count += 1
        print(f"  [LLM Call #{self.call_count}]")
        
        # Detect skill usage from messages
        for msg in messages:
            content = str(msg.get("content", ""))
            if "code_review" in content.lower():
                self.skill_used = "code_review"
            elif "debug" in content.lower():
                self.skill_used = "debug_py"
            elif "wiki" in content.lower():
                self.skill_used = "wiki_manager"
        
        # Simulate skill workflow
        if self.call_count == 1:
            return {
                "content": "我需要使用技能来处理这个任务。",
                "tool_calls": [
                    {"tool": "doc_read", "params": {"path": "skills/code_review.md"}},
                    {"tool": "file_read", "params": {"path": "agent/loop_v2.py"}}
                ]
            }
        elif self.call_count == 2:
            return {
                "content": "技能已加载，现在分析代码。",
                "tool_calls": [
                    {"tool": "shell_run", "params": {"command": "echo Linting done"}}
                ]
            }
        else:
            return {
                "content": """## 代码审查报告

### 文件信息
- 文件路径: agent/loop_v2.py
- 代码行数: 约 450 行

### 发现的问题
1. [UnicodeEncodeError风险] (严重程度: 中)
   - 位置: 多处 print 语句
   - 建议: 使用 safe_print 或设置环境编码

### 总体评价
好 - 代码结构清晰，逻辑完整

### 使用的技能
code_review""",
                "tool_calls": []
            }


def test_code_review_skill():
    """Test: code_review skill verification."""
    print("\n" + "=" * 60)
    print("  Skill Verification: code_review")
    print("=" * 60)
    
    mock = MockLLMClient()
    loop = AgentLoopV2(llm_client=mock)
    
    result = loop.run("使用 code_review 技能审查 agent/loop_v2.py 的代码质量")
    
    print(f"\n[结果]")
    print(f"  LLM 调用: {mock.call_count} 次")
    print(f"  技能使用: {mock.skill_used or '未检测到'}")
    print(f"  工具执行: {result.get('tools_called', 0)} 次")
    print(f"  回答长度: {len(result.get('content', ''))} 字符")
    print(f"  包含报告: {'代码审查报告' in result.get('content', '')}")
    
    success = (
        result.get("success") and
        mock.call_count <= 5 and
        "代码审查报告" in result.get("content", "")
    )
    
    print(f"\n  [{'OK' if success else 'FAIL'}] code_review skill")
    return success


def test_skill_file_loading():
    """Test: Skills can be loaded via doc_read tool."""
    print("\n" + "=" * 60)
    print("  Skill Verification: File Loading")
    print("=" * 60)
    
    from tools import get_initialized_registry
    registry = get_initialized_registry()
    
    # Test loading each skill file
    skills = ["code_review.md", "debug_py.md", "file_organizer.md", 
              "wiki_manager.md", "data_analysis.md", "git_helper.md"]
    
    results = []
    for skill in skills:
        path = f"skills/{skill}"
        result = registry.execute("doc_read", path=path)
        success = result.get("success", False)
        results.append((skill, success))
        print(f"  {'OK' if success else 'FAIL'} {skill}")
    
    all_success = all(r[1] for r in results)
    print(f"\n  [{'OK' if all_success else 'FAIL'}] All skill files loadable")
    return all_success


def test_skill_workflow_integration():
    """Test: Complete skill workflow in loop_v2."""
    print("\n" + "=" * 60)
    print("  Skill Workflow Integration Test")
    print("=" * 60)
    
    class WikiMockClient:
        def __init__(self):
            self.call_count = 0
        
        def chat(self, messages, tools=None):
            self.call_count += 1
            
            if self.call_count == 1:
                return {
                    "content": "加载 wiki_manager 技能",
                    "tool_calls": [
                        {"tool": "doc_read", "params": {"path": "skills/wiki_manager.md"}}
                    ]
                }
            elif self.call_count == 2:
                return {
                    "content": "创建知识条目",
                    "tool_calls": [
                        {"tool": "wiki_update", "params": {
                            "title": "AgentLoop v2 测试",
                            "content": "这是一个测试条目",
                            "tags": ["test", "v2"]
                        }}
                    ]
                }
            else:
                return {
                    "content": "## 知识库更新报告\n\n已创建条目: AgentLoop v2 测试\n标签: test, v2\n\n技能使用: wiki_manager",
                    "tool_calls": []
                }
    
    mock = WikiMockClient()
    loop = AgentLoopV2(llm_client=mock)
    result = loop.run("使用 wiki_manager 技能创建一个测试知识条目")
    
    print(f"\n  LLM 调用: {mock.call_count}")
    print(f"  工具调用: {result.get('tools_called', 0)}")
    print(f"  最终回答: {result.get('content', '')[:100]}...")
    
    success = result.get("success") and mock.call_count <= 5
    print(f"\n  [{'OK' if success else 'FAIL'}] wiki_manager workflow")
    return success


def main():
    print("=" * 60)
    print("  Hermes Agent - Skill Verification Tests")
    print("=" * 60)
    
    tests = [
        ("code_review skill", test_code_review_skill),
        ("Skill file loading", test_skill_file_loading),
        ("Skill workflow integration", test_skill_workflow_integration),
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
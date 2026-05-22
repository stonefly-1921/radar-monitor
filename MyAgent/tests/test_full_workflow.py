"""
Full workflow simulation test for Hermes Agent.
"""
import sys
import os
import json
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent.persona import Persona
from agent.config import AgentConfig
from memory.core import Memory
from tools import get_initialized_registry
from session import Session
from agent.loop import AgentLoop


def test_case_1_file_read():
    """Test Case 1: Read a file using file_read tool"""
    print("\n" + "="*60)
    print("Test Case 1: File Read Tool")
    print("="*60)
    
    # Create a test file
    test_file = os.path.join(tempfile.gettempdir(), "hermes_test_read.txt")
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write("Hello from Hermes!\nThis is a test file.\nLine 3")
    
    try:
        # Test file_read tool directly
        registry = get_initialized_registry()
        result = registry.execute("file_read", path=test_file)
        
        assert result["success"] == True
        assert "Hello from Hermes" in result["result"]
        print(f"  ✓ file_read returned: {result['result'][:50]}...")
        
        # Clean up
        os.unlink(test_file)
        print("  ✓ Test file cleaned up")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_case_2_file_write_and_edit():
    """Test Case 2: Write and edit files"""
    print("\n" + "="*60)
    print("Test Case 2: File Write and Edit")
    print("="*60)
    
    test_file = os.path.join(tempfile.gettempdir(), "hermes_test_write.txt")
    
    try:
        registry = get_initialized_registry()
        
        # Test file_write
        result = registry.execute("file_write", path=test_file, content="Original content")
        assert result["success"] == True
        print("  ✓ file_write successful")
        
        # Test file_edit
        result = registry.execute("file_edit", path=test_file, old_text="Original", new_text="Modified")
        assert result["success"] == True
        print("  ✓ file_edit successful")
        
        # Verify edit
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert "Modified content" in content
        print(f"  ✓ Verified content: {content}")
        
        # Clean up
        os.unlink(test_file)
        print("  ✓ Test file cleaned up")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_case_3_shell_command():
    """Test Case 3: Execute shell command"""
    print("\n" + "="*60)
    print("Test Case 3: Shell Command (dir)")
    print("="*60)
    
    try:
        registry = get_initialized_registry()
        
        # Test shell_run with dir command
        result = registry.execute("shell_run", command="dir /b", cwd=tempfile.gettempdir())
        
        print(f"  ✓ shell_run executed successfully")
        print(f"  Return code: {result.get('returncode', 'N/A')}")
        print(f"  Output preview: {str(result.get('result', ''))[:100]}...")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_case_4_python_run():
    """Test Case 4: Execute Python script"""
    print("\n" + "="*60)
    print("Test Case 4: Python Script Execution")
    print("="*60)
    
    try:
        registry = get_initialized_registry()
        
        script = """
import json
data = {"result": "success", "value": 42}
print(json.dumps(data))
"""
        result = registry.execute("python_run", script=script)
        
        assert result["success"] == True
        assert "42" in result["result"]
        print(f"  ✓ python_run executed successfully")
        print(f"  Output: {result['result'].strip()}")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_case_5_wiki_operations():
    """Test Case 5: Wiki search and update"""
    print("\n" + "="*60)
    print("Test Case 5: Wiki Operations")
    print("="*60)
    
    wiki_dir = os.path.join(tempfile.gettempdir(), "hermes_wiki_test")
    
    try:
        # Create temp wiki directory
        os.makedirs(wiki_dir, exist_ok=True)
        
        registry = get_initialized_registry()
        
        # Test wiki_update
        result = registry.execute("wiki_update", 
            title="Test Entry", 
            content="This is a test wiki entry for Hermes Agent.",
            tags=["test", "hermes"])
        
        assert result["success"] == True
        print(f"  ✓ wiki_update created entry")
        
        # Test wiki_search
        result = registry.execute("wiki_search", query="Hermes")
        
        assert result["success"] == True
        print(f"  ✓ wiki_search found {result.get('count', 0)} results")
        
        # Clean up
        shutil.rmtree(wiki_dir)
        print("  ✓ Wiki directory cleaned up")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        if os.path.exists(wiki_dir):
            shutil.rmtree(wiki_dir)
        return False


def test_case_6_session_persistence():
    """Test Case 6: Session creation and turn management"""
    print("\n" + "="*60)
    print("Test Case 6: Session Persistence")
    print("="*60)
    
    session_file = os.path.join(tempfile.gettempdir(), "hermes_test_session.json")
    
    try:
        # Create session
        session = Session.load_or_create(session_file)
        print(f"  ✓ Session created: {session.session_id}")
        
        # Add turns
        session.add_turn({
            "input": "First input",
            "final_answer": "First response"
        })
        session.add_turn({
            "input": "Second input",
            "tool_calls": [{"tool": "file_read", "params": {"path": "test.txt"}}],
            "tool_results": [{"tool": "file_read", "result": {"success": True, "result": "content"}}]
        })
        
        print(f"  ✓ Added 2 turns, total: {session.turn_count}")
        
        # Save session
        session.save()
        print(f"  ✓ Session saved")
        
        # Reload session
        session2 = Session.load_or_create(session_file)
        assert session2.turn_count == 2
        print(f"  ✓ Session reloaded, turns: {session2.turn_count}")
        
        # Clean up
        os.unlink(session_file)
        print("  ✓ Session file cleaned up")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        if os.path.exists(session_file):
            os.unlink(session_file)
        return False


def test_case_7_memory_management():
    """Test Case 7: Memory short-term and long-term"""
    print("\n" + "="*60)
    print("Test Case 7: Memory Management")
    print("="*60)
    
    try:
        memory = Memory()
        memory.clear()
        
        # Add short-term memory
        memory.add_turn("user", "User message 1")
        memory.add_turn("assistant", "Assistant response 1")
        memory.add_turn("user", "User message 2")
        
        print(f"  ✓ Short-term turns: {memory.turn_count}")
        
        # Add long-term memory
        memory.add_long_term("Important fact about the project", tags=["project", "important"])
        print(f"  ✓ Long-term entries: {len(memory.data['long_term'])}")
        
        # Search memory
        results = memory.search("project")
        print(f"  ✓ Search results: {len(results)} found")
        
        # Get context
        context = memory.get_context_for_llm()
        print(f"  ✓ Context built, conversation length: {len(context['conversation'])}")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_case_8_persona_system_prompt():
    """Test Case 8: Persona generates correct system prompt"""
    print("\n" + "="*60)
    print("Test Case 8: Persona System Prompt")
    print("="*60)
    
    try:
        persona = Persona()
        
        # Get system prompt
        prompt = persona.get_system_prompt()
        
        assert "Hermes" in prompt
        assert "智能助手" in prompt
        assert "文件操作" in prompt
        
        print(f"  ✓ System prompt generated ({len(prompt)} chars)")
        print(f"  ✓ Contains persona name: Hermes")
        print(f"  ✓ Contains role: 智能助手")
        print(f"  ✓ Contains capabilities")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_case_9_tools_registry():
    """Test Case 9: All tools are registered"""
    print("\n" + "="*60)
    print("Test Case 9: Tools Registry")
    print("="*60)
    
    try:
        registry = get_initialized_registry()
        tools = registry.list_tools()
        
        expected_tools = [
            "file_read", "file_write", "file_edit", "file_list",
            "shell_run", "python_run",
            "doc_read", "doc_write", "wiki_search", "wiki_update"
        ]
        
        print(f"  Total tools registered: {len(tools)}")
        
        for tool in expected_tools:
            if tool in tools:
                print(f"  ✓ {tool}")
            else:
                print(f"  ✗ {tool} - MISSING")
        
        return len(tools) == len(expected_tools)
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_case_10_full_prompt_generation():
    """Test Case 10: Full prompt generation workflow"""
    print("\n" + "="*60)
    print("Test Case 10: Full Prompt Generation")
    print("="*60)
    
    try:
        # Initialize components
        persona = Persona()
        registry = get_initialized_registry()
        
        # Create mock session
        session = Session()
        session._create_new()
        
        # Create memory
        memory = Memory()
        
        # Build a prompt as the agent loop would
        user_input = "帮我读取 README.md 文件"
        
        conversation_history = session.get_conversation_history()
        memory.add_turn("user", user_input)
        
        prompt = {
            "type": "prompt",
            "system": persona.get_system_prompt(),
            "context": {
                "session_id": session.session_id,
                "turn_count": session.turn_count + 1,
                "memory": memory.get_context_for_llm()
            },
            "conversation": conversation_history + [
                {"role": "user", "content": user_input}
            ],
            "tools_available": registry.get_all_specs(),
        }
        
        print(f"  ✓ Prompt built successfully")
        print(f"    System: {len(prompt['system'])} chars")
        print(f"    Context keys: {list(prompt['context'].keys())}")
        print(f"    Conversation: {len(prompt['conversation'])} messages")
        print(f"    Tools available: {len(prompt['tools_available'])}")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def main():
    print("="*60)
    print("  Hermes Agent - Full Workflow Simulation Test")
    print("="*60)
    
    tests = [
        ("File Read Tool", test_case_1_file_read),
        ("File Write and Edit", test_case_2_file_write_and_edit),
        ("Shell Command", test_case_3_shell_command),
        ("Python Execution", test_case_4_python_run),
        ("Wiki Operations", test_case_5_wiki_operations),
        ("Session Persistence", test_case_6_session_persistence),
        ("Memory Management", test_case_7_memory_management),
        ("Persona System Prompt", test_case_8_persona_system_prompt),
        ("Tools Registry", test_case_9_tools_registry),
        ("Full Prompt Generation", test_case_10_full_prompt_generation),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"  ✗ Test crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("  Test Summary")
    print("="*60)
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status} - {name}")
    
    print(f"\n  Total: {passed_count}/{total_count} passed")
    
    if passed_count == total_count:
        print("\n  🎉 All tests passed! Hermes Agent is ready to use.")
    else:
        print(f"\n  ⚠️  {total_count - passed_count} test(s) failed.")
    
    print("="*60)
    
    return passed_count == total_count


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
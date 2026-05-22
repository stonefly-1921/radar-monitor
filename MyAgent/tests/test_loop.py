"""
Tests for Agent Loop.
"""
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agent.loop import AgentLoop
from agent.config import AgentConfig


def test_agent_loop_initialization():
    """Test that AgentLoop initializes correctly."""
    config = AgentConfig()
    loop = AgentLoop(config=config)
    assert loop.persona is not None
    assert loop.registry is not None
    print("[PASS] test_agent_loop_initialization")


def test_prompt_structure():
    """Test that prompt has correct structure."""
    config = AgentConfig()
    loop = AgentLoop(config=config)
    loop.base_dir = os.path.join(os.path.dirname(__file__), '..')
    
    # Create a mock session
    from session import Session
    loop.session = Session()
    loop.session._create_new()
    
    # Create a mock memory
    from memory.core import Memory
    loop.memory = Memory()
    
    # Build prompt
    prompt = loop.build_prompt("Test input")
    
    assert "type" in prompt
    assert prompt["type"] == "prompt"
    assert "system" in prompt
    assert "conversation" in prompt
    assert "tools_available" in prompt
    print("[PASS] test_prompt_structure")


def test_response_parsing():
    """Test response parsing."""
    config = AgentConfig()
    loop = AgentLoop(config=config)
    
    # Test final answer parsing
    response = {"content": "This is a final answer"}
    result = loop.parse_response(response)
    assert result["type"] == "final_answer"
    assert result["content"] == "This is a final answer"
    
    # Test tool call parsing
    response = {
        "content": "Let me read that file",
        "tool_calls": [{"tool": "file_read", "params": {"path": "test.txt"}}]
    }
    result = loop.parse_response(response)
    assert result["type"] == "tool_call"
    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["tool"] == "file_read"
    
    print("[PASS] test_response_parsing")


def test_prompt_file_creation():
    """Test that prompt file is created correctly."""
    config = AgentConfig()
    loop = AgentLoop(config=config)
    loop.base_dir = os.path.join(os.path.dirname(__file__), '..')
    
    # Create mock session and memory
    from session import Session
    loop.session = Session()
    loop.session._create_new()
    
    from memory.core import Memory
    loop.memory = Memory()
    
    # Create a temp prompt file path
    prompt_file = os.path.join(tempfile.gettempdir(), "test_prompt.json")
    loop.io_config["prompt_file"] = prompt_file
    
    # Build and save prompt
    prompt = loop.build_prompt("Test input")
    loop.save_prompt(prompt)
    
    # Verify file was created
    assert os.path.exists(prompt_file)
    
    # Verify content
    with open(prompt_file, 'r', encoding='utf-8') as f:
        loaded = json.load(f)
    assert loaded["type"] == "prompt"
    assert len(loaded["conversation"]) == 1
    
    # Cleanup
    os.unlink(prompt_file)
    print("[PASS] test_prompt_file_creation")


if __name__ == "__main__":
    test_agent_loop_initialization()
    test_prompt_structure()
    test_response_parsing()
    test_prompt_file_creation()
    print("\n[OK] All loop tests passed!")
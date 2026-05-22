"""
Tests for Memory module.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from memory.core import Memory
from memory.context import ContextWindow
from memory.storage import MemoryStorage


def test_memory_initialization():
    """Test Memory initializes correctly."""
    m = Memory()
    assert m.data is not None
    assert "short_term" in m.data
    print("✓ test_memory_initialization passed")


def test_add_turn():
    """Test adding conversation turns."""
    m = Memory()
    m.clear()
    m.add_turn("user", "Hello")
    assert len(m.data["short_term"]) == 1
    assert m.data["short_term"][0]["content"] == "Hello"
    print("✓ test_add_turn passed")


def test_get_conversation():
    """Test retrieving conversation history."""
    m = Memory()
    m.clear()
    m.add_turn("user", "First")
    m.add_turn("assistant", "Second")
    conv = m.get_conversation()
    assert len(conv) == 2
    print("✓ test_get_conversation passed")


def test_search():
    """Test memory search."""
    m = Memory()
    m.clear()
    m.add_turn("user", "Tell me about Python")
    results = m.search("Python")
    assert len(results) >= 1
    print("✓ test_search passed")


def test_context_window():
    """Test context window truncation."""
    ctx = ContextWindow(max_turns=5)
    turns = [{"role": "user", "content": f"Turn {i}"} for i in range(10)]
    truncated = ctx.truncate(turns)
    assert len(truncated) == 5
    assert truncated[0]["content"] == "Turn 5"  # Last 5 turns
    print("✓ test_context_window passed")


def test_long_term_memory():
    """Test long-term memory storage."""
    m = Memory()
    m.clear()
    m.add_long_term("Important fact about the project", tags=["project"])
    assert len(m.data["long_term"]) == 1
    results = m.search("project")
    assert len(results) >= 1
    print("✓ test_long_term_memory passed")


def test_summarize():
    """Test memory summarization."""
    m = Memory()
    m.clear()
    m.summarize("This is a summary of previous conversation")
    assert len(m.data["summaries"]) == 1
    print("✓ test_summarize passed")


def test_memory_turn_count():
    """Test turn count property."""
    m = Memory()
    m.clear()
    assert m.turn_count == 0
    m.add_turn("user", "Hello")
    assert m.turn_count == 1
    print("✓ test_memory_turn_count passed")


if __name__ == "__main__":
    test_memory_initialization()
    test_add_turn()
    test_get_conversation()
    test_search()
    test_context_window()
    test_long_term_memory()
    test_summarize()
    test_memory_turn_count()
    print("\n✓ All memory tests passed!")
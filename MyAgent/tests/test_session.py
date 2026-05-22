"""
Tests for Session management.
"""
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from session import Session


def test_session_creation():
    """Test creating a new session."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = f.name
    
    try:
        session = Session.load_or_create(temp_path)
        assert session.session_id is not None
        assert session.status == "in_progress"
        assert session.turn_count == 0
        print("[PASS] test_session_creation")
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_add_turn():
    """Test adding a turn to session."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = f.name
    
    try:
        session = Session.load_or_create(temp_path)
        session.add_turn({
            "input": "Hello",
            "final_answer": "Hi there!"
        })
        assert session.turn_count == 1
        print("[PASS] test_add_turn passed")
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_save_and_load():
    """Test saving and loading a session."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = f.name
    
    try:
        # Create and save session
        session1 = Session.load_or_create(temp_path)
        session1.add_turn({"input": "Test input"})
        session1.save()
        
        # Load session
        session2 = Session.load_or_create(temp_path)
        assert session2.turn_count == 1
        assert session2.turns[0]["input"] == "Test input"
        print("[PASS] test_save_and_load passed")
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_conversation_history():
    """Test getting conversation history."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = f.name
    
    try:
        session = Session.load_or_create(temp_path)
        session.add_turn({"input": "First", "final_answer": "Response 1"})
        session.add_turn({"input": "Second", "final_answer": "Response 2"})
        
        history = session.get_conversation_history()
        assert len(history) == 4  # 2 user + 2 assistant
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "First"
        print("[PASS] test_conversation_history passed")
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_mark_completed():
    """Test marking session as completed."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = f.name
    
    try:
        session = Session.load_or_create(temp_path)
        session.mark_completed()
        assert session.status == "completed"
        print("[PASS] test_mark_completed passed")
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_to_dict():
    """Test session export to dict."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = f.name
    
    try:
        session = Session.load_or_create(temp_path)
        session.add_turn({"input": "Test"})
        
        data = session.to_dict()
        assert "session_id" in data
        assert "turn_count" in data
        assert data["turn_count"] == 1
        print("[PASS] test_to_dict passed")
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


if __name__ == "__main__":
    test_session_creation()
    test_add_turn()
    test_save_and_load()
    test_conversation_history()
    test_mark_completed()
    test_to_dict()
    print("\n[PASS] All session tests passed!")
"""
Tests for file operation tools.
"""
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.file_ops import FileReadTool, FileWriteTool, FileEditTool, FileListTool


def test_file_write_and_read():
    """Test writing and reading a file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
        temp_path = f.name
        f.write("Hello, World!")
    
    try:
        tool = FileReadTool()
        result = tool.execute(path=temp_path)
        assert result["success"] is True
        assert "Hello, World!" in result["result"]
        print("[PASS] test_file_write_and_read")
    finally:
        os.unlink(temp_path)


def test_file_write():
    """Test FileWriteTool."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
        temp_path = f.name
    
    try:
        tool = FileWriteTool()
        result = tool.execute(path=temp_path, content="Test content")
        assert result["success"] is True
        assert os.path.exists(temp_path)
        print("[PASS] test_file_write")
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_file_edit():
    """Test FileEditTool."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
        temp_path = f.name
        f.write("Hello, World!")
    
    try:
        tool = FileEditTool()
        result = tool.execute(path=temp_path, old_text="World", new_text="Hermes")
        assert result["success"] is True
        
        # Verify edit
        with open(temp_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == "Hello, Hermes!"
        print("[PASS] test_file_edit")
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_file_list():
    """Test FileListTool."""
    tool = FileListTool()
    
    # List current directory
    result = tool.execute(path=".")
    assert result["success"] is True
    assert "files" in result or "result" in result
    print("[PASS] test_file_list")


def test_file_read_nonexistent():
    """Test reading a non-existent file."""
    tool = FileReadTool()
    result = tool.execute(path="nonexistent_file_12345.txt")
    assert result["success"] is False
    assert "不存在" in result["error"]
    print("[PASS] test_file_read_nonexistent")


def test_file_list_nonexistent():
    """Test listing a non-existent directory."""
    tool = FileListTool()
    result = tool.execute(path="nonexistent_directory_12345")
    assert result["success"] is False
    assert "不存在" in result["error"]
    print("[PASS] test_file_list_nonexistent")


if __name__ == "__main__":
    test_file_write_and_read()
    test_file_write()
    test_file_edit()
    test_file_list()
    test_file_read_nonexistent()
    test_file_list_nonexistent()
    print("\n[OK] All file_ops tests passed!")
"""
Tests for doc/wiki tools.
"""
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.doc_wiki import (
    DocReadTool, DocWriteTool, 
    WikiSearchTool, WikiUpdateTool
)


def test_doc_write_and_read():
    """Test writing and reading a document."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md', encoding='utf-8') as f:
        temp_path = f.name
        f.write("# Test Document\nHello, Hermes!")
    
    try:
        tool = DocReadTool()
        result = tool.execute(path=temp_path)
        assert result["success"] is True
        assert "Test Document" in result["result"]
        print("✓ test_doc_write_and_read passed")
    finally:
        os.unlink(temp_path)


def test_wiki_update_and_search():
    """Test wiki update and search."""
    temp_wiki_dir = tempfile.mkdtemp()
    
    try:
        # Create wiki tool with temp directory
        update_tool = WikiUpdateTool(wiki_dir=temp_wiki_dir)
        result = update_tool.execute(
            title="Test Entry",
            content="This is a test entry about Python.",
            tags=["test", "python"]
        )
        assert result["success"] is True
        
        # Search for the entry
        search_tool = WikiSearchTool(wiki_dir=temp_wiki_dir)
        search_result = search_tool.execute(query="Python")
        assert search_result["success"] is True
        assert search_result["count"] >= 1
        print("✓ test_wiki_update_and_search passed")
    finally:
        shutil.rmtree(temp_wiki_dir)


def test_doc_read_nonexistent():
    """Test reading a non-existent document."""
    tool = DocReadTool()
    result = tool.execute(path="nonexistent_doc_12345.md")
    assert result["success"] is False
    assert "不存在" in result["error"]
    print("✓ test_doc_read_nonexistent passed")


if __name__ == "__main__":
    test_doc_write_and_read()
    test_wiki_update_and_search()
    test_doc_read_nonexistent()
    print("\n✓ All doc/wiki tests passed!")

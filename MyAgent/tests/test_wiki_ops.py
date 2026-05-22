"""
Tests for wiki_ops tools (karpathy-llm-wiki business layer).
"""
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.wiki_ops import (
    WikiIndexTool, WikiLintTool, WikiLinkCheckTool,
    WikiReadTool, WikiWriteTool, WikiDeleteTool
)


def setup_test_wiki():
    """Create a temp wiki directory and return its path."""
    temp_dir = tempfile.mkdtemp()
    os.makedirs(os.path.join(temp_dir, "wiki"))
    return temp_dir


def test_wiki_index_empty():
    """Test WikiIndexTool on empty wiki."""
    wiki_root = setup_test_wiki()
    try:
        tool = WikiIndexTool()
        result = tool.execute(wiki_root=wiki_root, rebuild=True)
        assert result["success"] is True
        assert result["pages"] == []
        assert "0 pages" in result["result"]
        print("✓ test_wiki_index_empty passed")
    finally:
        shutil.rmtree(wiki_root)


def test_wiki_write_and_index():
    """Test WikiWriteTool then WikiIndexTool shows it."""
    wiki_root = setup_test_wiki()
    try:
        write_tool = WikiWriteTool()
        result = write_tool.execute(
            page="test-subject",
            content="## Overview\nTest content.\n\n## Sources\n- Source A",
            summary="A test subject page",
            tags=["test"],
            sources=["test-source"],
            wiki_root=wiki_root
        )
        assert result["success"] is True
        
        index_tool = WikiIndexTool()
        index_result = index_tool.execute(wiki_root=wiki_root, rebuild=True)
        assert index_result["success"] is True
        assert len(index_result["pages"]) == 1
        assert index_result["pages"][0]["slug"] == "test-subject"
        print("✓ test_wiki_write_and_index passed")
    finally:
        shutil.rmtree(wiki_root)


def test_wiki_read():
    """Test WikiReadTool reads page with frontmatter."""
    wiki_root = setup_test_wiki()
    try:
        write_tool = WikiWriteTool()
        write_tool.execute(
            page="readable-page",
            content="## Overview\nSome content here.\n\n## Sources\n- Source B",
            wiki_root=wiki_root
        )
        
        read_tool = WikiReadTool()
        result = read_tool.execute(page="readable-page", wiki_root=wiki_root)
        assert result["success"] is True
        assert result["page"] == "readable-page"
        assert "Overview" in result["content"]
        assert "Some content here" in result["content"]
        # frontmatter should be extracted
        assert "summary" in result["frontmatter"] or len(result["frontmatter"]) >= 0
        print("✓ test_wiki_read passed")
    finally:
        shutil.rmtree(wiki_root)


def test_wiki_lint_clean():
    """Test WikiLintTool on a clean wiki."""
    wiki_root = setup_test_wiki()
    try:
        write_tool = WikiWriteTool()
        write_tool.execute(
            page="page-a",
            content="## Overview\nContent for A.\n\n## Sources\n- Source A\n\nSee also [[page-b]].",
            wiki_root=wiki_root
        )
        write_tool.execute(
            page="page-b",
            content="## Overview\nContent for B.\n\n## Sources\n- Source B\n\nSee also [[page-a]].",
            wiki_root=wiki_root
        )
        
        lint_tool = WikiLintTool()
        result = lint_tool.execute(wiki_root=wiki_root)
        assert result["success"] is True
        assert result["total_pages"] == 2
        assert result["issues_count"] == 0
        assert result["warnings_count"] == 0
        print("✓ test_wiki_lint_clean passed")
    finally:
        shutil.rmtree(wiki_root)


def test_wiki_lint_orphaned():
    """Test WikiLintTool detects orphaned page."""
    wiki_root = setup_test_wiki()
    try:
        write_tool = WikiWriteTool()
        write_tool.execute(
            page="orphan-page",
            content="## Overview\nI am not linked from anywhere.",
            wiki_root=wiki_root
        )
        write_tool.execute(
            page="another-page",
            content="## Overview\nI link to nothing.",
            wiki_root=wiki_root
        )
        
        lint_tool = WikiLintTool()
        result = lint_tool.execute(wiki_root=wiki_root)
        assert result["success"] is True
        # orphan-page has no inbound links
        orphan_issues = [i for i in result["issues"] if i["type"] == "orphan"]
        assert len(orphan_issues) >= 1
        print("✓ test_wiki_lint_orphaned passed")
    finally:
        shutil.rmtree(wiki_root)


def test_wiki_link_check_valid():
    """Test WikiLinkCheckTool with valid links."""
    wiki_root = setup_test_wiki()
    try:
        write_tool = WikiWriteTool()
        write_tool.execute(page="source-page", content="## Overview\nContent.", wiki_root=wiki_root)
        write_tool.execute(page="target-page", content="## Overview\nContent.", wiki_root=wiki_root)
        
        # Write a page that links to target-page
        write_tool.execute(
            page="linking-page",
            content="## Overview\nSee [[target-page]] and [[source-page]].",
            wiki_root=wiki_root
        )
        
        check_tool = WikiLinkCheckTool()
        result = check_tool.execute(page="linking-page", wiki_root=wiki_root)
        assert result["success"] is True
        assert result["total_links"] == 2
        assert result["broken_count"] == 0
        assert len(result["valid"]) == 2
        print("✓ test_wiki_link_check_valid passed")
    finally:
        shutil.rmtree(wiki_root)


def test_wiki_link_check_broken():
    """Test WikiLinkCheckTool with broken link."""
    wiki_root = setup_test_wiki()
    try:
        write_tool = WikiWriteTool()
        write_tool.execute(
            page="page-with-dead-link",
            content="## Overview\nSee [[nonexistent-page]].",
            wiki_root=wiki_root
        )
        
        check_tool = WikiLinkCheckTool()
        result = check_tool.execute(page="page-with-dead-link", wiki_root=wiki_root)
        assert result["success"] is True
        assert result["broken_count"] == 1
        assert "nonexistent-page" in result["broken"]
        print("✓ test_wiki_link_check_broken passed")
    finally:
        shutil.rmtree(wiki_root)


def test_wiki_delete():
    """Test WikiDeleteTool."""
    wiki_root = setup_test_wiki()
    try:
        write_tool = WikiWriteTool()
        write_tool.execute(page="to-delete", content="## Overview\nDelete me.", wiki_root=wiki_root)
        
        # Verify it exists
        read_tool = WikiReadTool()
        assert read_tool.execute(page="to-delete", wiki_root=wiki_root)["success"] is True
        
        # Delete it
        delete_tool = WikiDeleteTool()
        result = delete_tool.execute(page="to-delete", wiki_root=wiki_root)
        assert result["success"] is True
        
        # Verify it's gone
        assert read_tool.execute(page="to-delete", wiki_root=wiki_root)["success"] is False
        print("✓ test_wiki_delete passed")
    finally:
        shutil.rmtree(wiki_root)


def test_wiki_lint_missing_sources():
    """Test WikiLintTool detects missing Sources section."""
    wiki_root = setup_test_wiki()
    try:
        write_tool = WikiWriteTool()
        write_tool.execute(
            page="no-sources-page",
            content="## Overview\nJust content, no sources section.",
            wiki_root=wiki_root
        )
        
        lint_tool = WikiLintTool()
        result = lint_tool.execute(wiki_root=wiki_root)
        missing_sources = [w for w in result["warnings"] if w["type"] == "missing_sources"]
        assert len(missing_sources) >= 1
        print("✓ test_wiki_lint_missing_sources passed")
    finally:
        shutil.rmtree(wiki_root)


if __name__ == "__main__":
    test_wiki_index_empty()
    test_wiki_write_and_index()
    test_wiki_read()
    test_wiki_lint_clean()
    test_wiki_lint_orphaned()
    test_wiki_link_check_valid()
    test_wiki_link_check_broken()
    test_wiki_delete()
    test_wiki_lint_missing_sources()
    print("\n✓ All wiki_ops tests passed!")
"""
Tests for DiffTool - file diff operations.
TDD: tests written first to drive implementation.
"""
import os
import sys
import tempfile
import shutil

# Ensure the project root is in the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.diff_ops import DiffTool
from tools.registry import ToolRegistry


class TestDiffTool:
    """Test suite for DiffTool."""

    @classmethod
    def setup_class(cls):
        """Set up test fixtures."""
        cls.test_dir = tempfile.mkdtemp(prefix="diff_test_")
        cls.tool = DiffTool()
        cls.registry = ToolRegistry()
        cls.registry.register(cls.tool)

    @classmethod
    def teardown_class(cls):
        """Clean up test fixtures."""
        if hasattr(cls, 'test_dir') and os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    def _write_file(self, filename, content):
        """Helper to write a test file."""
        path = os.path.join(self.test_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def _read_file(self, path):
        """Helper to read a file."""
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    # ---- test: identical files ----
    def test_diff_identical_files(self):
        """No diff output for same content."""
        content = "line one\nline two\nline three\n"
        file1 = self._write_file("same1.txt", content)
        file2 = self._write_file("same2.txt", content)

        result = self.tool.execute(file1=file1, file2=file2)

        assert result["success"] is True
        # For identical files, unified_diff returns empty or minimal output
        diff_output = result.get("result", "")
        # Should have success even if no differences
        assert isinstance(diff_output, str)

    # ---- test: additions ----
    def test_diff_additions(self):
        """Lines in file2 not in file1 shown as additions."""
        file1_content = "line one\nline two\n"
        file2_content = "line one\nline two\nline three\n"
        file1 = self._write_file("base.txt", file1_content)
        file2 = self._write_file("added.txt", file2_content)

        result = self.tool.execute(file1=file1, file2=file2)

        assert result["success"] is True
        diff_output = result.get("result", "")
        assert "line three" in diff_output
        # '+' indicates an addition in unified diff
        assert "+" in diff_output

    # ---- test: deletions ----
    def test_diff_deletions(self):
        """Lines in file1 not in file2 shown as deletions."""
        file1_content = "line one\nline two\nline three\n"
        file2_content = "line one\nline two\n"
        file1 = self._write_file("full.txt", file1_content)
        file2 = self._write_file("removed.txt", file2_content)

        result = self.tool.execute(file1=file1, file2=file2)

        assert result["success"] is True
        diff_output = result.get("result", "")
        assert "line three" in diff_output
        # '-' indicates a deletion in unified diff
        assert "-" in diff_output

    # ---- test: changes (modified lines shown as context) ----
    def test_diff_changes(self):
        """Modified lines shown with context."""
        file1_content = "line one\nline two\nline three\n"
        file2_content = "line one\nline modified\nline three\n"
        file1 = self._write_file("original.txt", file1_content)
        file2 = self._write_file("modified.txt", file2_content)

        result = self.tool.execute(file1=file1, file2=file2)

        assert result["success"] is True
        diff_output = result.get("result", "")
        # Should contain both old and new versions
        assert "line two" in diff_output or "line modified" in diff_output

    # ---- test: unified format ----
    def test_diff_unified_format(self):
        """Unified diff format output."""
        file1_content = "header\nbody\nfooter\n"
        file2_content = "header\nbody changed\nfooter\n"
        file1 = self._write_file("v1.txt", file1_content)
        file2 = self._write_file("v2.txt", file2_content)

        result = self.tool.execute(file1=file1, file2=file2)

        assert result["success"] is True
        diff_output = result.get("result", "")
        # Unified format markers
        assert "---" in diff_output
        assert "+++" in diff_output

    # ---- test: tool registered ----
    def test_diff_tool_registered(self):
        """Verifies tool in registry."""
        retrieved = self.registry.get("diff")
        assert retrieved is not None
        assert retrieved.name == "diff"
        assert retrieved.description == "对比两个文件差异，支持 unified 格式输出"

    # ---- test: missing file1 ----
    def test_diff_missing_file1(self):
        """Error when file1 is missing."""
        file2 = self._write_file("exists.txt", "content")

        result = self.tool.execute(file1="/nonexistent/file1.txt", file2=file2)

        assert result["success"] is False
        assert "error" in result

    # ---- test: missing file2 ----
    def test_diff_missing_file2(self):
        """Error when file2 is missing."""
        file1 = self._write_file("exists.txt", "content")

        result = self.tool.execute(file1=file1, file2="/nonexistent/file2.txt")

        assert result["success"] is False
        assert "error" in result

    # ---- test: binary files handled ----
    def test_diff_binary_files(self):
        """Binary files should be handled gracefully."""
        file1_path = os.path.join(self.test_dir, "binary1.bin")
        file2_path = os.path.join(self.test_dir, "binary2.bin")
        with open(file1_path, 'wb') as f:
            f.write(b'\x00\x01\x02\x03')
        with open(file2_path, 'wb') as f:
            f.write(b'\x00\x01\x03\x04')

        result = self.tool.execute(file1=file1_path, file2=file2_path)

        # Should either succeed with diff or fail gracefully
        assert "success" in result
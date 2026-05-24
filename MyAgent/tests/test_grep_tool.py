"""
Tests for grep operation tool.
"""
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.grep_ops import GrepTool


class TestGrepTool(object):
    """Test class for GrepTool."""

    def setup_method(self):
        """Create temp directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.tool = GrepTool()

    def teardown_method(self):
        """Clean up temp directory."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_grep_finds_matching_lines(self):
        """Test basic grep functionality - finds matching lines."""
        # Create test file
        test_file = os.path.join(self.temp_dir, "test.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("line 1: hello world\n")
            f.write("line 2: python is great\n")
            f.write("line 3: hello again\n")

        result = self.tool.execute(path=self.temp_dir, pattern="hello")

        assert result["success"] is True
        matches = result["result"]
        assert len(matches) == 2
        assert matches[0]["file"] == test_file
        assert "hello" in matches[0]["content"]
        print("[PASS] test_grep_finds_matching_lines")

    def test_grep_recursive(self):
        """Test recursive directory searching."""
        # Create nested structure
        sub_dir = os.path.join(self.temp_dir, "subdir")
        os.makedirs(sub_dir)

        file1 = os.path.join(self.temp_dir, "file1.txt")
        file2 = os.path.join(sub_dir, "file2.txt")

        with open(file1, 'w', encoding='utf-8') as f:
            f.write("main file content\n")

        with open(file2, 'w', encoding='utf-8') as f:
            f.write("nested file content\n")

        result = self.tool.execute(path=self.temp_dir, pattern="content", recursive=True)

        assert result["success"] is True
        matches = result["result"]
        assert len(matches) == 2
        print("[PASS] test_grep_recursive")

    def test_grep_case_insensitive(self):
        """Test case insensitive matching."""
        test_file = os.path.join(self.temp_dir, "case_test.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("Hello WORLD\n")
            f.write("hello world\n")
            f.write("HELLO World\n")

        # Case sensitive - only exact match
        result_cs = self.tool.execute(path=self.temp_dir, pattern="Hello", case_sensitive=True)
        assert result_cs["success"] is True
        assert len(result_cs["result"]) == 1

        # Case insensitive - matches all
        result_ci = self.tool.execute(path=self.temp_dir, pattern="hello", case_sensitive=False)
        assert result_ci["success"] is True
        assert len(result_ci["result"]) == 3
        print("[PASS] test_grep_case_insensitive")

    def test_grep_regex_pattern(self):
        """Test regex pattern matching."""
        test_file = os.path.join(self.temp_dir, "regex_test.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("file2024.txt\n")
            f.write("file2023.txt\n")
            f.write("other.txt\n")

        # Match files with year pattern
        result = self.tool.execute(path=self.temp_dir, pattern=r"file\d{4}\.txt", regex=True)

        assert result["success"] is True
        matches = result["result"]
        assert len(matches) == 2
        print("[PASS] test_grep_regex_pattern")

    def test_grep_no_match(self):
        """Test when no matches are found."""
        test_file = os.path.join(self.temp_dir, "empty.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("hello world\n")

        result = self.tool.execute(path=self.temp_dir, pattern="nonexistent")

        assert result["success"] is True
        assert result["result"] == []
        print("[PASS] test_grep_no_match")

    def test_grep_tool_registered(self):
        """Test that grep tool is registered in the tool registry."""
        from tools import get_initialized_registry

        registry = get_initialized_registry()
        tool = registry.get("grep")

        assert tool is not None
        assert tool.name == "grep"
        print("[PASS] test_grep_tool_registered")


if __name__ == "__main__":
    # Run tests manually for simple output
    test_instance = TestGrepTool()

    try:
        test_instance.setup_method()
        test_instance.test_grep_finds_matching_lines()
    except Exception as e:
        print("[FAIL] test_grep_finds_matching_lines:", str(e))

    try:
        test_instance.teardown_method()
        test_instance.setup_method()
        test_instance.test_grep_recursive()
    except Exception as e:
        print("[FAIL] test_grep_recursive:", str(e))

    try:
        test_instance.teardown_method()
        test_instance.setup_method()
        test_instance.test_grep_case_insensitive()
    except Exception as e:
        print("[FAIL] test_grep_case_insensitive:", str(e))

    try:
        test_instance.teardown_method()
        test_instance.setup_method()
        test_instance.test_grep_regex_pattern()
    except Exception as e:
        print("[FAIL] test_grep_regex_pattern:", str(e))

    try:
        test_instance.teardown_method()
        test_instance.setup_method()
        test_instance.test_grep_no_match()
    except Exception as e:
        print("[FAIL] test_grep_no_match:", str(e))

    try:
        test_instance.teardown_method()
        test_instance.test_grep_tool_registered()
    except Exception as e:
        print("[FAIL] test_grep_tool_registered:", str(e))

    print("\n[OK] All grep tests completed!")
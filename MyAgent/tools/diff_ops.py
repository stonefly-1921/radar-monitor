"""
Diff tool - compare two files and show differences in unified diff format.
Pure Python stdlib only: os, difflib, pathlib.
Python 3.7.4 compatible (no f-strings, no walrus, no async).
"""
import os
import difflib

from .base import Tool


class DiffTool(Tool):
    """
    Compare two files and return differences in unified diff format.
    """

    name = "diff"
    description = "对比两个文件差异，支持 unified 格式输出"
    parameters = [
        {
            "name": "file1",
            "type": "string",
            "required": True,
            "description": "第一个文件路径（原始文件）"
        },
        {
            "name": "file2",
            "type": "string",
            "required": True,
            "description": "第二个文件路径（比较文件）"
        }
    ]

    def execute(self, **kwargs):
        """
        Execute the diff operation.

        Args:
            file1: Path to the first (original) file
            file2: Path to the second (comparison) file

        Returns:
            dict: Result containing 'success', 'result' (diff text), and optional 'error'
        """
        file1 = kwargs.get("file1")
        file2 = kwargs.get("file2")

        # Validate required parameters
        if not file1:
            return {"success": False, "error": "缺少必需参数: file1"}
        if not file2:
            return {"success": False, "error": "缺少必需参数: file2"}

        # Check file1 exists
        if not os.path.isfile(file1):
            return {"success": False, "error": "文件不存在: " + file1}

        # Check file2 exists
        if not os.path.isfile(file2):
            return {"success": False, "error": "文件不存在: " + file2}

        try:
            # Read file contents with encoding detection
            encoding1 = self._detect_encoding(file1)
            encoding2 = self._detect_encoding(file2)

            with open(file1, 'r', encoding=encoding1) as f:
                lines1 = f.readlines()

            with open(file2, 'r', encoding=encoding2) as f:
                lines2 = f.readlines()

            # Compute unified diff
            diff_lines = list(difflib.unified_diff(
                lines1,
                lines2,
                fromfile=file1,
                tofile=file2,
                lineterm=''
            ))

            diff_output = '\n'.join(diff_lines)

            return {
                "success": True,
                "result": diff_output if diff_output else "(两个文件完全相同)",
                "file1": file1,
                "file2": file2,
                "changes": len(diff_lines)
            }

        except IOError as e:
            return {"success": False, "error": "文件读取错误: " + str(e)}
        except Exception as e:
            return {"success": False, "error": "diff 操作失败: " + str(e)}

    def validate(self, params):
        """
        Validate tool parameters.

        Args:
            params: dict of parameters

        Returns:
            tuple: (is_valid, error_message)
        """
        if "file1" not in params:
            return False, "缺少必需参数: file1"
        if "file2" not in params:
            return False, "缺少必需参数: file2"
        return True, None

    def _detect_encoding(self, path):
        """
        Detect file encoding without external dependencies.
        Tries common encodings in order of likelihood.
        """
        encodings = [
            'utf-8',
            'utf-8-sig',  # UTF-8 with BOM
            'gbk',        # Chinese Windows
            'gb2312',     # Chinese
            'gb18030',    # Chinese (extended)
            'latin-1',    # Fallback for Western
            'cp1252',     # Windows Western
        ]

        for enc in encodings:
            try:
                with open(path, 'r', encoding=enc) as f:
                    f.read()
                return enc
            except (UnicodeDecodeError, LookupError):
                continue

        return 'utf-8'


def register_tools(registry):
    """Register the DiffTool with the registry."""
    registry.register(DiffTool())
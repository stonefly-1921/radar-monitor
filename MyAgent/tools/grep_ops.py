"""
Grep operation tool - search for patterns in files.
No external dependencies - uses only Python built-ins.
"""
import os
import re
from .base import Tool


class GrepTool(Tool):
    """Search for patterns in files recursively."""

    name = "grep"
    description = "递归搜索目录中包含关键词的文件，支持正则和大小写不敏感"
    parameters = [
        {"name": "path", "type": "string", "required": True, "description": "搜索目录路径"},
        {"name": "pattern", "type": "string", "required": True, "description": "搜索关键词或正则表达式"},
        {"name": "case_sensitive", "type": "boolean", "required": False, "description": "是否大小写敏感，默认True"},
        {"name": "recursive", "type": "boolean", "required": False, "description": "是否递归搜索子目录，默认True"},
        {"name": "regex", "type": "boolean", "required": False, "description": "是否使用正则表达式，默认False"}
    ]

    def execute(self, **kwargs):
        path = kwargs.get("path")
        pattern = kwargs.get("pattern")
        case_sensitive = kwargs.get("case_sensitive", True)
        recursive = kwargs.get("recursive", True)
        regex = kwargs.get("regex", False)

        if not path:
            return {"success": False, "error": "缺少搜索路径参数"}
        if not pattern:
            return {"success": False, "error": "缺少搜索模式参数"}

        # Validate path exists
        if not os.path.exists(path):
            return {"success": False, "error": "路径不存在: " + path}

        matches = []

        try:
            if os.path.isfile(path):
                # Single file
                file_matches = self._search_file(path, pattern, case_sensitive, regex)
                matches.extend(file_matches)
            elif os.path.isdir(path):
                # Directory
                if recursive:
                    matches = self._search_recursive(path, pattern, case_sensitive, regex)
                else:
                    matches = self._search_directory(path, pattern, case_sensitive, regex)
        except Exception as e:
            return {"success": False, "error": "搜索失败: " + str(e)}

        return {
            "success": True,
            "result": matches,
            "count": len(matches)
        }

    def _search_file(self, filepath, pattern, case_sensitive, regex):
        """Search a single file for pattern matches."""
        matches = []

        # Determine if file is text (readable)
        if not self._is_text_file(filepath):
            return matches

        try:
            encoding = self._detect_encoding(filepath)
            with open(filepath, 'r', encoding=encoding, errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    if self._line_matches(line, pattern, case_sensitive, regex):
                        matches.append({
                            "file": filepath,
                            "line": line_num,
                            "content": line.rstrip('\r\n')
                        })
        except Exception:
            # Skip files that can't be read
            pass

        return matches

    def _search_directory(self, directory, pattern, case_sensitive, regex):
        """Search files in a directory (non-recursive)."""
        matches = []

        try:
            for entry in os.listdir(directory):
                filepath = os.path.join(directory, entry)
                if os.path.isfile(filepath):
                    file_matches = self._search_file(filepath, pattern, case_sensitive, regex)
                    matches.extend(file_matches)
        except Exception:
            pass

        return matches

    def _search_recursive(self, directory, pattern, case_sensitive, regex):
        """Recursively search all files in directory."""
        matches = []

        for root, dirs, files in os.walk(directory):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for filename in files:
                # Skip hidden files
                if filename.startswith('.'):
                    continue
                filepath = os.path.join(root, filename)
                file_matches = self._search_file(filepath, pattern, case_sensitive, regex)
                matches.extend(file_matches)

        return matches

    def _line_matches(self, line, pattern, case_sensitive, regex):
        """Check if a line matches the pattern."""
        if regex:
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                return re.search(pattern, line, flags) is not None
            except re.error:
                # Invalid regex, fall back to literal match
                return False
        else:
            line_cmp = line if case_sensitive else line.lower()
            pattern_cmp = pattern if case_sensitive else pattern.lower()
            return pattern_cmp in line_cmp

    def _is_text_file(self, filepath):
        """Check if a file is likely a text file."""
        # Check extension first
        text_extensions = (
            '.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.yaml', '.yml',
            '.md', '.rst', '.log', '.cfg', '.ini', '.conf', '.sh', '.bat', '.ps1',
            '.c', '.cpp', '.h', '.hpp', '.java', '.go', '.rs', '.rb', '.php',
            '.sql', '.csv', '.tsv', '.env', '.gitignore', '.dockerignore'
        )
        ext = os.path.splitext(filepath)[1].lower()
        if ext in text_extensions:
            return True

        # Binary file signatures
        binary_signatures = (
            b'\x89PNG', b'\xff\xd8\xff', b'GIF', b'PK\x03\x04',  # images, zip
            b'MZ', b'\x7fELF',  # executables
        )

        try:
            with open(filepath, 'rb') as f:
                header = f.read(8)
                for sig in binary_signatures:
                    if isinstance(sig, bytes) and header.startswith(sig):
                        return False
                # Check for null bytes (common in binary)
                for byte in header:
                    if byte == 0:
                        return False
        except Exception:
            return False

        return True

    def _detect_encoding(self, filepath):
        """Detect file encoding."""
        encodings = [
            'utf-8',
            'utf-8-sig',
            'gbk',
            'gb2312',
            'gb18030',
            'latin-1',
            'cp1252',
        ]

        for enc in encodings:
            try:
                with open(filepath, 'r', encoding=enc) as f:
                    f.read()
                return enc
            except (UnicodeDecodeError, LookupError):
                continue

        return 'utf-8'

    def validate(self, params):
        """Validate tool parameters."""
        if "path" not in params:
            return False, "缺少必需参数: path"
        if "pattern" not in params:
            return False, "缺少必需参数: pattern"
        return True, None


# Register tools
def register_tools(registry):
    """Register grep tool."""
    registry.register(GrepTool())
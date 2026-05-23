"""
File operation tools - read, write, edit, list files.
No external dependencies - uses only Python built-ins.
"""
import os
import glob
from .base import Tool


def detect_encoding(path):
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


class FileReadTool(Tool):
    """Read contents of a file."""
    
    name = "file_read"
    description = "读取文件内容"
    parameters = [
        {"name": "path", "type": "string", "required": True, "description": "文件路径"}
    ]
    
    def execute(self, **kwargs):
        path = kwargs.get("path")
        if not path:
            return {"success": False, "error": "缺少文件路径参数"}
        
        try:
            encoding = detect_encoding(path)
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            
            return {
                "success": True,
                "result": content,
                "path": path,
                "lines": len(content.splitlines())
            }
        except FileNotFoundError:
            return {"success": False, "error": f"文件不存在: {path}"}
        except Exception as e:
            return {"success": False, "error": f"读取文件失败: {str(e)}"}
    
    def validate(self, params):
        if "path" not in params:
            return False, "缺少必需参数: path"
        return True, None


class FileWriteTool(Tool):
    """Write content to a file."""
    
    name = "file_write"
    description = "写入内容到文件"
    parameters = [
        {"name": "path", "type": "string", "required": True, "description": "文件路径"},
        {"name": "content", "type": "string", "required": True, "description": "写入内容"}
    ]
    
    def execute(self, **kwargs):
        path = kwargs.get("path")
        content = kwargs.get("content", "")
        
        if not path:
            return {"success": False, "error": "缺少文件路径参数"}
        
        try:
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "result": f"成功写入 {len(content)} 个字符到 {path}",
                "path": path,
                "bytes": len(content.encode('utf-8'))
            }
        except Exception as e:
            return {"success": False, "error": f"写入文件失败: {str(e)}"}
    
    def validate(self, params):
        if "path" not in params:
            return False, "缺少必需参数: path"
        return True, None


class FileEditTool(Tool):
    """Edit a file by replacing text."""
    
    name = "file_edit"
    description = "编辑文件内容（替换）"
    parameters = [
        {"name": "path", "type": "string", "required": True, "description": "文件路径"},
        {"name": "old_text", "type": "string", "required": True, "description": "要被替换的文本"},
        {"name": "new_text", "type": "string", "required": True, "description": "替换后的文本"}
    ]
    
    def execute(self, **kwargs):
        path = kwargs.get("path")
        old_text = kwargs.get("old_text")
        new_text = kwargs.get("new_text")
        
        if not path:
            return {"success": False, "error": "缺少文件路径参数"}
        if old_text is None:
            return {"success": False, "error": "缺少 old_text 参数"}
        
        try:
            encoding = detect_encoding(path)
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            
            if old_text not in content:
                return {"success": False, "error": f"未找到要替换的文本: {old_text[:50]}..."}
            
            new_content = content.replace(old_text, new_text, 1)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return {
                "success": True,
                "result": f"成功替换文件内容",
                "path": path,
                "replacements": 1
            }
        except FileNotFoundError:
            return {"success": False, "error": f"文件不存在: {path}"}
        except Exception as e:
            return {"success": False, "error": f"编辑文件失败: {str(e)}"}
    
    def validate(self, params):
        if "path" not in params:
            return False, "缺少必需参数: path"
        if "old_text" not in params:
            return False, "缺少必需参数: old_text"
        return True, None


class FileListTool(Tool):
    """List files in a directory."""
    
    name = "file_list"
    description = "列出目录中的文件"
    parameters = [
        {"name": "path", "type": "string", "required": True, "description": "目录路径"},
        {"name": "pattern", "type": "string", "required": False, "description": "文件匹配模式（如 *.py）"}
    ]
    
    def _fix_windows_path(self, path):
        """修复 Windows 路径中缺少反斜杠的问题。
        例如：'C:Users15041Desktop' → 'C:\\Users\\15041\\Desktop'
        检测驱动器字母后没有反斜杠的情况。
        """
        import re
        # 检测驱动器路径格式：C: 或 D: 开头但没有反斜杠
        # 例如 C:Users → C:\Users (但 C:\Users 保持不变)
        match = re.match(r'^([A-Za-z]):([^\\/])', path)
        if match:
            drive = match.group(1)
            rest = match.group(2)
            # 将 C:Users 转换为 C:\Users
            return f'{drive}:\\{rest}'
        return path
    
    def execute(self, **kwargs):
        path = kwargs.get("path")
        pattern = kwargs.get("pattern", "*")
        
        if not path:
            return {"success": False, "error": "缺少目录路径参数"}
        
        # 修复 Windows 路径问题（C:Users → C:\Users）
        path = self._fix_windows_path(path)
        
        try:
            if not os.path.exists(path):
                return {"success": False, "error": f"目录不存在: {path}"}
            
            if not os.path.isdir(path):
                return {"success": False, "error": f"路径不是目录: {path}"}
            
            if pattern and pattern != "*":
                search_path = os.path.join(path, pattern)
                files = glob.glob(search_path)
                try:
                    entries = os.listdir(path)
                    for entry in entries:
                        full_path = os.path.join(path, entry)
                        if os.path.isdir(full_path) and self._matches_pattern(entry, pattern):
                            files.append(full_path)
                except:
                    pass
            else:
                files = []
                entries = os.listdir(path)
                for entry in entries:
                    files.append(os.path.join(path, entry))
            
            result_files = []
            result_dirs = []
            for f in sorted(files):
                if os.path.isdir(f):
                    result_dirs.append(os.path.basename(f) + "/")
                else:
                    result_files.append(os.path.basename(f))
            
            return {
                "success": True,
                "result": result_files + result_dirs,
                "path": path,
                "count": len(result_files) + len(result_dirs),
                "files": result_files,
                "directories": result_dirs
            }
        except Exception as e:
            return {"success": False, "error": f"列出目录失败: {str(e)}"}
    
    def _matches_pattern(self, name, pattern):
        import fnmatch
        return fnmatch.fnmatch(name, pattern)
    
    def validate(self, params):
        if "path" not in params:
            return False, "缺少必需参数: path"
        return True, None


# Register all tools
def register_tools(registry):
    """Register all file operation tools."""
    registry.register(FileReadTool())
    registry.register(FileWriteTool())
    registry.register(FileEditTool())
    registry.register(FileListTool())
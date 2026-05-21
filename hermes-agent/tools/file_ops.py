"""
File operation tools - read, write, edit, list files.
"""
import os
import glob
import chardet
from .base import Tool


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
            # Detect encoding
            with open(path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result.get('encoding', 'utf-8') or 'utf-8'
            
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
            # Ensure directory exists
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
            # Detect encoding
            with open(path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result.get('encoding', 'utf-8') or 'utf-8'
            
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            
            if old_text not in content:
                return {"success": False, "error": f"未找到要替换的文本: {old_text[:50]}..."}
            
            new_content = content.replace(old_text, new_text, 1)  # Replace first occurrence only
            
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
    
    def execute(self, **kwargs):
        path = kwargs.get("path")
        pattern = kwargs.get("pattern", "*")
        
        if not path:
            return {"success": False, "error": "缺少目录路径参数"}
        
        try:
            if not os.path.exists(path):
                return {"success": False, "error": f"目录不存在: {path}"}
            
            if not os.path.isdir(path):
                return {"success": False, "error": f"路径不是目录: {path}"}
            
            # Handle pattern
            if pattern and pattern != "*":
                search_path = os.path.join(path, pattern)
                files = glob.glob(search_path)
                # Also get directory names if they match
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
            
            # Sort and format results
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
        """Check if filename matches pattern."""
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
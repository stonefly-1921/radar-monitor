"""
Python script execution tool.
"""
import subprocess
import sys
import os
import tempfile
from .base import Tool
from .shell import ShellRunTool


class PythonRunTool(Tool):
    """Execute Python scripts."""
    
    name = "python_run"
    description = "执行Python脚本"
    parameters = [
        {"name": "script", "type": "string", "required": True, "description": "Python代码"},
        {"name": "timeout", "type": "int", "required": False, "description": "超时时间（秒）"}
    ]
    
    def __init__(self, python_path=None, timeout=120):
        self.python_path = python_path or sys.executable
        self.default_timeout = timeout
    
    def execute(self, **kwargs):
        script = kwargs.get("script")
        timeout = kwargs.get("timeout", self.default_timeout)
        
        if not script:
            return {"success": False, "error": "缺少脚本参数"}
        
        try:
            # Write script to temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py', encoding='utf-8') as f:
                f.write(script)
                temp_path = f.name
            
            try:
                # Execute script
                # 强制子进程用 UTF-8 输出，解决 Windows 控制台 GBK 乱码问题
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                result = subprocess.run(
                    [self.python_path, temp_path],
                    capture_output=True,
                    timeout=timeout,
                    encoding='utf-8',
                    errors='replace',
                    env=env
                )
                
                output = result.stdout if result.stdout else ""
                error_output = result.stderr if result.stderr else ""
                
                return {
                    "success": result.returncode == 0,
                    "result": output,
                    "error": error_output if error_output else None,
                    "returncode": result.returncode
                }
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Python脚本执行超时（{timeout}秒）"}
        except FileNotFoundError:
            return {"success": False, "error": f"Python解释器未找到: {self.python_path}"}
        except Exception as e:
            return {"success": False, "error": f"Python脚本执行失败: {str(e)}"}
    
    def validate(self, params):
        if "script" not in params:
            return False, "缺少必需参数: script"
        return True, None


def register_tools(registry):
    """Register Python execution tool."""
    registry.register(PythonRunTool())

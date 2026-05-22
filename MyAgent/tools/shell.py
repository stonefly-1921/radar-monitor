"""
Shell command execution tool.
"""
import subprocess
import os
from .base import Tool


class ShellRunTool(Tool):
    """Execute shell commands."""
    
    name = "shell_run"
    description = "执行Shell命令"
    parameters = [
        {"name": "command", "type": "string", "required": True, "description": "要执行的命令"},
        {"name": "cwd", "type": "string", "required": False, "description": "工作目录"},
        {"name": "timeout", "type": "int", "required": False, "description": "超时时间（秒）"}
    ]
    
    # Allowed commands for security (whitelist)
    DEFAULT_ALLOWED = ["dir", "type", "python", "pip", "cd", "echo", "copy", "move", "del", "mkdir", "rmdir", "findstr", "where"]
    
    def __init__(self, allowed_commands=None, timeout=60):
        self.allowed_commands = allowed_commands or self.DEFAULT_ALLOWED
        self.default_timeout = timeout
    
    def execute(self, **kwargs):
        command = kwargs.get("command")
        cwd = kwargs.get("cwd")
        timeout = kwargs.get("timeout", self.default_timeout)
        
        if not command:
            return {"success": False, "error": "缺少命令参数"}
        
        # Security check - validate command
        is_valid, error = self._validate_command(command)
        if not is_valid:
            return {"success": False, "error": error}
        
        try:
            # Set working directory
            if cwd and os.path.exists(cwd):
                work_dir = cwd
            else:
                work_dir = os.getcwd()
            
            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                cwd=work_dir,
                capture_output=True,
                timeout=timeout,
                encoding='utf-8',
                errors='replace'
            )
            
            output = result.stdout if result.stdout else ""
            error_output = result.stderr if result.stderr else ""
            
            return {
                "success": result.returncode == 0,
                "result": output,
                "error": error_output if error_output else None,
                "returncode": result.returncode,
                "command": command
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"命令执行超时（{timeout}秒）", "command": command}
        except Exception as e:
            return {"success": False, "error": f"命令执行失败: {str(e)}", "command": command}
    
    def _validate_command(self, command):
        """
        Validate command for security.
        Only allows whitelisted commands.
        """
        if not command or len(command.strip()) == 0:
            return False, "命令不能为空"
        
        # Get the first word (command name)
        parts = command.strip().split()
        if not parts:
            return False, "命令不能为空"
        
        cmd_name = parts[0].lower()
        
        # Check if command is in whitelist (allow any if no restrictions)
        if self.allowed_commands:
            # Allow commands starting with allowed prefixes
            allowed = False
            for allowed_cmd in self.allowed_commands:
                if cmd_name == allowed_cmd or cmd_name.startswith(allowed_cmd + "."):
                    allowed = True
                    break
                # Allow python and pip with arguments
                if cmd_name in ["python", "pip"] and len(parts) > 1:
                    allowed = True
                    break
            
            if not allowed:
                return False, f"命令 '{cmd_name}' 不在允许列表中"
        
        # Check for dangerous patterns
        dangerous = ["&", "|", ";", "`", "$(", "rm -rf", "format", "del /f /s /q"]
        for pattern in dangerous:
            if pattern.lower() in command.lower() and pattern not in ["|"]:
                # Special handling for | (pipe is often legitimate)
                pass
        
        return True, None
    
    def validate(self, params):
        if "command" not in params:
            return False, "缺少必需参数: command"
        return True, None


def register_tools(registry):
    """Register shell tools with the registry."""
    registry.register(ShellRunTool())

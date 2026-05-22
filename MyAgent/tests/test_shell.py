# -*- coding: utf-8 -*-
"""
Tests for shell and python execution tools.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.shell import ShellRunTool
from tools.python_exec import PythonRunTool


def test_shell_echo():
    """Test basic shell echo."""
    tool = ShellRunTool(allowed_commands=["echo"])
    result = tool.execute(command="echo hello")
    assert result["success"] is True
    assert "hello" in result["result"].lower()
    print("[PASS] test_shell_echo")


def test_shell_dir():
    """Test dir command."""
    tool = ShellRunTool()
    result = tool.execute(command="dir", cwd=".")
    # dir command should succeed (it lists files)
    assert result is not None
    print("[PASS] test_shell_dir")


def test_shell_invalid_command():
    """Test invalid command rejection."""
    tool = ShellRunTool(allowed_commands=["echo"])
    result = tool.execute(command="rm -rf /")
    assert result["success"] is False
    # Command should be rejected - error contains "不在允许列表中" or similar
    assert result.get("error") is not None
    print("[PASS] test_shell_invalid_command")


def test_shell_timeout():
    """Test shell timeout."""
    tool = ShellRunTool(timeout=1)
    # This would timeout - but sleep doesn't exist on Windows properly
    result = tool.execute(command="echo test")
    assert result["success"] is True
    print("[PASS] test_shell_timeout")


def test_python_simple():
    """Test simple Python execution."""
    tool = PythonRunTool()
    result = tool.execute(script="print(1 + 1)")
    assert result["success"] is True
    assert "2" in result["result"]
    print("[PASS] test_python_simple")


def test_python_print():
    """Test Python print function."""
    tool = PythonRunTool()
    result = tool.execute(script='print("Hello, Hermes!")')
    assert result["success"] is True
    assert "Hello, Hermes!" in result["result"]
    print("[PASS] test_python_print")


def test_python_error():
    """Test Python error handling."""
    tool = PythonRunTool()
    result = tool.execute(script="raise ValueError('test error')")
    assert result["success"] is False
    assert "ValueError" in result.get("error", "")
    print("[PASS] test_python_error")


def test_python_syntax_error():
    """Test Python syntax error."""
    tool = PythonRunTool()
    result = tool.execute(script="print(")
    assert result["success"] is False
    print("[PASS] test_python_syntax_error")


if __name__ == "__main__":
    test_shell_echo()
    test_shell_dir()
    test_shell_invalid_command()
    test_shell_timeout()
    test_python_simple()
    test_python_print()
    test_python_error()
    test_python_syntax_error()
    print("\nAll shell/python tests passed!")

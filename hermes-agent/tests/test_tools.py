"""
Tests for Tools module.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.base import Tool
from tools.registry import ToolRegistry, get_registry


class DummyTool(Tool):
    """A dummy tool for testing."""
    name = "dummy"
    description = "A dummy tool for testing"
    parameters = [
        {"name": "text", "type": "string", "required": True}
    ]
    
    def execute(self, **kwargs):
        return {
            "success": True,
            "result": "Got: {}".format(kwargs.get('text', ''))
        }


def test_tool_registry_singleton():
    """Test that registry is a singleton."""
    r1 = get_registry()
    r2 = get_registry()
    assert r1 is r2
    print("[PASS] test_tool_registry_singleton")


def test_register_tool():
    """Test tool registration."""
    registry = ToolRegistry()
    registry.clear()
    tool = DummyTool()
    registry.register(tool)
    assert "dummy" in registry.list_tools()
    print("[PASS] test_register_tool")


def test_unregister_tool():
    """Test tool unregistration."""
    registry = ToolRegistry()
    registry.clear()
    tool = DummyTool()
    registry.register(tool)
    registry.unregister("dummy")
    assert "dummy" not in registry.list_tools()
    print("[PASS] test_unregister_tool")


def test_get_tool():
    """Test getting a tool by name."""
    registry = ToolRegistry()
    registry.clear()
    tool = DummyTool()
    registry.register(tool)
    retrieved = registry.get("dummy")
    assert retrieved is tool
    print("[PASS] test_get_tool")


def test_execute_tool():
    """Test tool execution through registry."""
    registry = ToolRegistry()
    registry.clear()
    tool = DummyTool()
    registry.register(tool)
    result = registry.execute("dummy", text="hello")
    assert result["success"] is True
    assert "hello" in result["result"]
    print("[PASS] test_execute_tool")


def test_execute_nonexistent_tool():
    """Test executing a non-existent tool."""
    registry = ToolRegistry()
    registry.clear()
    result = registry.execute("nonexistent")
    assert result["success"] is False
    assert "not found" in result["error"]
    print("[PASS] test_execute_nonexistent_tool")


def test_tool_spec():
    """Test tool specification generation."""
    tool = DummyTool()
    spec = tool.get_spec()
    assert spec["name"] == "dummy"
    assert "parameters" in spec
    print("[PASS] test_tool_spec")


def test_list_tools():
    """Test listing all tools."""
    registry = ToolRegistry()
    registry.clear()
    assert len(registry.list_tools()) == 0
    registry.register(DummyTool())
    assert len(registry.list_tools()) == 1
    print("[PASS] test_list_tools")


if __name__ == "__main__":
    test_tool_registry_singleton()
    test_register_tool()
    test_unregister_tool()
    test_get_tool()
    test_execute_tool()
    test_execute_nonexistent_tool()
    test_tool_spec()
    test_list_tools()
    print("\n[SUCCESS] All tool tests passed!")
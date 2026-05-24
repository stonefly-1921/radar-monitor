# -*- coding: utf-8 -*-
"""
Tests for process_status tool.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.process_status_ops import ProcessStatusTool


def test_process_status_returns_list():
    """Verify process_status returns a list."""
    tool = ProcessStatusTool()
    result = tool.execute()
    assert isinstance(result, list), "Result should be a list"
    print("[PASS] test_process_status_returns_list")


def test_process_status_has_required_fields():
    """Each entry has name, pid, memory_mb."""
    tool = ProcessStatusTool()
    result = tool.execute()
    assert len(result) > 0, "Should return at least one process"
    for entry in result:
        assert "name" in entry, "Entry missing 'name' field"
        assert "pid" in entry, "Entry missing 'pid' field"
        assert "memory_mb" in entry, "Entry missing 'memory_mb' field"
        # pid should be convertible to int
        assert isinstance(entry["pid"], int), "pid should be an integer"
        # memory_mb should be a number (int or float)
        assert isinstance(entry["memory_mb"], (int, float)), "memory_mb should be a number"
    print("[PASS] test_process_status_has_required_fields")


def test_process_status_tool_registered():
    """Verify tool is registered in registry."""
    from tools import get_initialized_registry
    registry = get_initialized_registry()
    tool = registry.get("process_status")
    assert tool is not None, "process_status tool should be registered"
    print("[PASS] test_process_status_tool_registered")


def test_process_status_command_used():
    """Verify a command was actually run to get process list."""
    tool = ProcessStatusTool()
    result = tool.execute()
    # Should return non-empty list on any system
    assert len(result) > 0, "Should have parsed output from a command"
    # Verify we have system process names
    names = [e["name"] for e in result]
    # At least one common Windows process should appear
    common = ["System", "Idle", "python", "cmd", "explorer"]
    found = any(c.lower() in [n.lower() for n in names] for c in common)
    assert found, "Should find at least one common Windows process: %s" % names[:5]
    print("[PASS] test_process_status_command_used")


if __name__ == "__main__":
    test_process_status_returns_list()
    test_process_status_has_required_fields()
    test_process_status_tool_registered()
    test_process_status_command_used()
    print("\nAll process_status tests passed!")
# -*- coding: utf-8 -*-
"""
Test for Task E2: Merge log panel + final answer into a single unified display.
TDD Phase: RED (write failing tests first)

These tests verify:
- _final_answer_text no longer exists in MyAgentWindow
- _exec_log_text is the only log container
- _write_final_answer() inserts separator "=== 最终回答 ==="
- Final answer content appears after separator in _exec_log_text
- Panel expands with content (no separate final answer widget)
"""
import unittest
import sys
import os

# Ensure the agent package is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestMergedLogPanel(unittest.TestCase):
    """Tests for merged log panel (Task E2)."""

    @classmethod
    def setUpClass(cls):
        """Create a hidden root window shared across all tests in this class."""
        import tkinter as tk
        cls._shared_root = tk.Tk()
        cls._shared_root.withdraw()

    @classmethod
    def tearDownClass(cls):
        """Destroy the shared root after all tests complete."""
        cls._shared_root.update()
        cls._shared_root.destroy()

    def setUp(self):
        """Re-use the shared root for each test."""
        self.root = self._shared_root
        self.root.update()

    def test_final_answer_text_removed(self):
        """Verify _final_answer_text no longer exists in MyAgentWindow."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        self.assertFalse(
            hasattr(win, '_final_answer_text'),
            "_final_answer_text should be removed from MyAgentWindow"
        )

    def test_single_log_panel_exists(self):
        """Verify _exec_log_text is the only log container."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        self.assertIsNotNone(win._exec_log_text)
        # _exec_log_text should be a Text widget
        import tkinter as tk
        self.assertIsInstance(win._exec_log_text, tk.Text)

    def test_separator_inserted_before_final_answer(self):
        """Calling _write_final_answer() inserts '=== 最终回答 ===' separator."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()

        # Ensure _write_final_answer method exists
        self.assertTrue(
            hasattr(win, '_write_final_answer'),
            "MyAgentWindow should have _write_final_answer method"
        )

        # Call _write_final_answer with test content
        test_content = "这是测试最终回答"
        win._write_final_answer(test_content)

        # Check that separator appears in _exec_log_text
        import tkinter as tk
        log_content = win._exec_log_text.get("1.0", tk.END)
        self.assertIn("=== 最终回答 ===", log_content)

    def test_final_answer_inserted_after_separator(self):
        """Content appears after separator in _exec_log_text."""
        from agent.ui import MyAgentWindow
        import tkinter as tk
        win = MyAgentWindow(self.root)
        self.root.update()

        test_content = "这是测试最终回答内容"
        win._write_final_answer(test_content)

        log_content = win._exec_log_text.get("1.0", tk.END)
        # Find position of separator
        sep_pos = log_content.find("=== 最终回答 ===")
        content_pos = log_content.find(test_content, sep_pos)
        self.assertGreater(
            content_pos, sep_pos,
            "Final answer content should appear after the separator"
        )

    def test_log_panel_grows_with_content(self):
        """Panel expands as content is added, no separate final answer widget."""
        from agent.ui import MyAgentWindow
        import tkinter as tk
        win = MyAgentWindow(self.root)
        self.root.update()

        # Verify no separate final answer widget exists
        self.assertFalse(
            hasattr(win, '_final_answer_text'),
            "No separate _final_answer_text should exist"
        )

        # Get initial line count
        initial_lines = int(win._exec_log_text.index(tk.END).split('.')[0])

        # Add log entries
        win.append_log("USER", "开始任务: 测试任务")
        win.append_log("AGENT", "思考中...")
        win.append_log("TOOL", "调用工具...")

        # Process the queue
        self.root.update()
        import time
        time.sleep(0.2)
        self.root.update()

        # Add final answer
        win._write_final_answer("这是最终回答内容，测试面板扩展")

        self.root.update()
        time.sleep(0.2)
        self.root.update()

        # Get final line count
        final_lines = int(win._exec_log_text.index(tk.END).split('.')[0])

        # Lines should have increased with all the content
        self.assertGreater(
            final_lines, initial_lines,
            "Log panel should grow as content is added"
        )

    def test_write_final_answer_method_exists(self):
        """Verify _write_final_answer method exists and is callable."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        self.assertTrue(hasattr(win, '_write_final_answer'))
        self.assertTrue(callable(getattr(win, '_write_final_answer')))

    def test_separator_followed_by_newline(self):
        """Separator should be followed by newline and then content."""
        import tkinter as tk
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()

        win._write_final_answer("测试内容")
        log_content = win._exec_log_text.get("1.0", tk.END)

        sep_idx = log_content.find("=== 最终回答 ===")
        self.assertNotEqual(sep_idx, -1, "Separator should be present")
        # After separator there should be newline + content
        self.assertEqual(log_content[sep_idx + len("=== 最终回答 ==="):].strip(), "测试内容")


if __name__ == '__main__':
    unittest.main()
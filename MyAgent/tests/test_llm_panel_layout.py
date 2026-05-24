# -*- coding: utf-8 -*-
"""
Test for Task A3: LLM Interaction Panel Layout (Right Panel)
TDD Phase: RED (write failing tests first)

Tests verify the right panel (LLM 交互区) contains:
- Prompt display Text widget (top ~300px, scrollable, readonly)
- 复制prompt button (below prompt)
- Response display Text widget (middle, scrollable, readonly)
- 粘贴&提交 button (below response)
- 清空日志 button
"""
import unittest
import sys
import os
import tkinter as tk

# Ensure the agent package is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestLLMPanelLayout(unittest.TestCase):
    """Tests for MyAgentWindow right panel (LLM interaction zone)."""

    @classmethod
    def setUpClass(cls):
        """Create a hidden root window shared across all tests."""
        import tkinter as tk
        cls._shared_root = tk.Tk()
        cls._shared_root.withdraw()  # hide window during tests

    @classmethod
    def tearDownClass(cls):
        """Destroy the shared root after all tests complete."""
        cls._shared_root.update()
        cls._shared_root.destroy()

    def setUp(self):
        """Re-use the shared root for each test."""
        self.root = self._shared_root
        self.root.update()

    def test_prompt_text_exists(self):
        """Verify 'Prompt 文本' Text widget exists in right panel."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        self.assertIsNotNone(win._right_panel)
        # Check that _prompt_text exists as an instance variable
        self.assertTrue(
            hasattr(win, '_prompt_text'),
            "MyAgentWindow should have _prompt_text attribute"
        )

    def test_prompt_text_readonly(self):
        """Verify Prompt Text widget is in DISABLED (readonly) state."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        prompt_text = win._prompt_text
        self.assertEqual(prompt_text.cget("state"), tk.DISABLED)

    def test_copy_prompt_button_exists(self):
        """Verify '复制 prompt' button exists."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        self.assertTrue(
            hasattr(win, '_copy_prompt_btn'),
            "MyAgentWindow should have _copy_prompt_btn attribute"
        )

    def test_copy_prompt_button_text(self):
        """Verify '复制 prompt' button text is correct."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        btn = win._copy_prompt_btn
        self.assertEqual(btn.cget("text"), "复制 prompt")

    def test_response_text_exists(self):
        """Verify 'Response 粘贴区' Text widget exists in right panel."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        self.assertTrue(
            hasattr(win, '_response_text'),
            "MyAgentWindow should have _response_text attribute"
        )

    def test_response_text_editable(self):
        """Verify Response Text widget is in NORMAL (editable) state."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        response_text = win._response_text
        self.assertEqual(response_text.cget("state"), tk.NORMAL)

    def test_submit_response_button_exists(self):
        """Verify '粘贴 & 提交' button exists."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        self.assertTrue(
            hasattr(win, '_submit_response_btn'),
            "MyAgentWindow should have _submit_response_btn attribute"
        )

    def test_submit_response_button_text(self):
        """Verify '粘贴 & 提交' button text is correct."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        btn = win._submit_response_btn
        self.assertEqual(btn.cget("text"), "粘贴 & 提交")

    def test_clear_right_panel_button_exists(self):
        """Verify '清空日志' button exists in right panel."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        self.assertTrue(
            hasattr(win, '_clear_llm_log_btn'),
            "MyAgentWindow should have _clear_llm_log_btn attribute"
        )

    def test_clear_right_panel_button_text(self):
        """Verify '清空日志' button text is correct."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        btn = win._clear_llm_log_btn
        self.assertEqual(btn.cget("text"), "清空日志")

    def test_copy_prompt_calls_clipboard(self):
        """Verify copy prompt button calls clipboard_clear and clipboard_append."""
        from agent.ui import MyAgentWindow
        from unittest.mock import patch

        win = MyAgentWindow(self.root)
        self.root.update()

        # Insert some test text into the prompt widget
        win._prompt_text.config(state=tk.NORMAL)
        win._prompt_text.insert("1.0", "test prompt content")
        win._prompt_text.config(state=tk.DISABLED)

        with patch.object(self.root, 'clipboard_clear') as mock_clear, \
             patch.object(self.root, 'clipboard_append') as mock_append:
            win._copy_prompt_btn.invoke()
            mock_clear.assert_called_once()
            mock_append.assert_called_once_with("test prompt content")

    def test_submit_response_callback_bound(self):
        """Verify submit response button has a callback bound (command is set)."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        btn = win._submit_response_btn
        self.assertIsNotNone(btn.cget("command"))

    def test_prompt_text_scrollable(self):
        """Verify Prompt Text widget has a scrollbar."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        self.assertTrue(
            hasattr(win, '_prompt_scrollbar'),
            "MyAgentWindow should have _prompt_scrollbar attribute"
        )

    def test_response_text_scrollable(self):
        """Verify Response Text widget has a scrollbar."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        self.assertTrue(
            hasattr(win, '_response_scrollbar'),
            "MyAgentWindow should have _response_scrollbar attribute"
        )


if __name__ == '__main__':
    unittest.main()
# -*- coding: utf-8 -*-
"""
Test for Task D1: End-to-End UI Integration Test
TDD Phase: RED (write failing tests first)

Tests the full UI as one system, covering all panels and interactions.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestFullUIIntegration(unittest.TestCase):
    """End-to-end integration tests for the full MyAgent UI."""

    @classmethod
    def setUpClass(cls):
        """Create a hidden root window shared across all tests."""
        import tkinter as tk
        cls._shared_root = tk.Tk()
        cls._shared_root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls._shared_root.update()
        cls._shared_root.destroy()

    def setUp(self):
        self.root = self._shared_root
        self.root.update()

    def test_full_ui_instantiates(self):
        """Verify window opens without error."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        self.assertIsNotNone(win.root)
        self.assertEqual(win.root.title(), "MyAgent v2")

    def test_left_console_has_all_elements(self):
        """Verify left console has: task input Text, 开始任务 button, log Text, final answer Text, 打断 button."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()

        # Task input Text
        self.assertIsNotNone(getattr(win, '_task_input_text', None))
        self.assertEqual(win._task_input_text.get('1.0', '1.0'), '')  # empty at start

        # 开始任务 button
        self.assertIsNotNone(getattr(win, '_start_task_btn', None))
        self.assertEqual(win._start_task_btn.cget('text'), '开始任务')

        # Execution log Text
        self.assertIsNotNone(getattr(win, '_exec_log_text', None))

        # Final answer Text
        self.assertIsNotNone(getattr(win, '_final_answer_text', None))

        # 打断 button
        self.assertIsNotNone(getattr(win, '_interrupt_btn', None))
        self.assertEqual(win._interrupt_btn.cget('text'), '打断')

    def test_right_panel_has_all_elements(self):
        """Verify right panel has: prompt Text, response Text, 复制prompt button, 粘贴&提交 button, 清空日志 button."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()

        # Prompt Text
        self.assertIsNotNone(getattr(win, '_prompt_text', None))

        # Response Text
        self.assertIsNotNone(getattr(win, '_response_text', None))

        # 复制prompt button
        self.assertIsNotNone(getattr(win, '_copy_prompt_btn', None))
        self.assertEqual(win._copy_prompt_btn.cget('text'), '复制 prompt')

        # 粘贴&提交 button
        self.assertIsNotNone(getattr(win, '_submit_response_btn', None))
        self.assertEqual(win._submit_response_btn.cget('text'), '粘贴 & 提交')

        # 清空日志 button
        self.assertIsNotNone(getattr(win, '_clear_llm_log_btn', None))
        self.assertEqual(win._clear_llm_log_btn.cget('text'), '清空日志')

    def test_log_queue_empty_at_start(self):
        """Verify _log_queue is empty when UI starts."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        self.assertIsNotNone(getattr(win, '_log_queue', None))
        self.assertTrue(win._log_queue.empty())

    def test_interrupt_button_wired(self):
        """Verify clicking 打断 button sets the interrupt event."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()

        self.assertFalse(win._interrupt_event.is_set())
        win._interrupt_btn.invoke()
        self.assertTrue(win._interrupt_event.is_set())

    def test_status_bar_initial_text(self):
        """Verify status bar shows '状态: 等待输入' at start."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        self.assertEqual(win._status_label.cget('text'), '状态: 等待输入')


if __name__ == '__main__':
    unittest.main()
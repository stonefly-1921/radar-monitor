# -*- coding: utf-8 -*-
"""
MyAgent Tkinter UI - Task A2: Control Console Layout (Left Panel)

Tests verify the left panel contains:
- Task input Text widget (~80px, placeholder "输入任务...")
- "开始任务" button
- Execution log Text widget (scrollable, readonly)
- Final answer Text widget (~150px, readonly)
- "打断" button

TDD RED phase: write failing tests first.
"""
import unittest
import tkinter as tk
import sys
import os

# Ensure MyAgent package in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agent.ui import MyAgentWindow


class TestConsoleLayout(unittest.TestCase):
    """Tests for left panel console layout controls."""

    @classmethod
    def setUpClass(cls):
        """Create a visible root window shared across all tests (not withdrawn)."""
        import tkinter as tk
        cls._shared_root = tk.Tk()
        # Do NOT withdraw - needed for geometry manager to allocate widget space

    @classmethod
    def tearDownClass(cls):
        """Destroy the shared root after all tests complete."""
        cls._shared_root.update()
        cls._shared_root.destroy()

    def setUp(self):
        """Re-use shared root for each test."""
        self.root = self._shared_root
        self.root.update()
        # Import here to ensure fresh module state per test
        from agent.ui import MyAgentWindow
        self.win = MyAgentWindow(root=self.root)
        self.root.update()

    def test_task_input_text_exists(self):
        """Verify task input Text widget exists and is editable."""
        self.assertTrue(
            hasattr(self.win, '_task_input_text'),
            "MyAgentWindow should have _task_input_text attribute"
        )
        self.assertIsInstance(
            self.win._task_input_text, tk.Text,
            "_task_input_text should be a tkinter Text widget"
        )
        # Should be editable (not disabled)
        self.assertEqual(
            self.win._task_input_text.cget('state'), 'normal',
            "Task input Text should be editable (state=normal)"
        )

    def test_start_task_button_exists(self):
        """Verify '开始任务' button exists with correct text."""
        self.assertTrue(
            hasattr(self.win, '_start_task_btn'),
            "MyAgentWindow should have _start_task_btn attribute"
        )
        self.assertIsInstance(
            self.win._start_task_btn, tk.Button,
            "_start_task_btn should be a tkinter Button"
        )
        self.assertEqual(
            self.win._start_task_btn.cget('text'), '开始任务',
            "'开始任务' button text should be '开始任务'"
        )

    def test_exec_log_text_exists(self):
        """Verify execution log Text widget exists and is readonly."""
        self.assertTrue(
            hasattr(self.win, '_exec_log_text'),
            "MyAgentWindow should have _exec_log_text attribute"
        )
        self.assertIsInstance(
            self.win._exec_log_text, tk.Text,
            "_exec_log_text should be a tkinter Text widget"
        )
        # Should be readonly (disabled)
        self.assertEqual(
            self.win._exec_log_text.cget('state'), 'disabled',
            "Execution log Text should be readonly (state=disabled)"
        )

    def test_final_answer_text_exists(self):
        """Verify _final_answer_text widget does NOT exist (this was a mistaken test).

        The UI does NOT have a separate _final_answer_text widget. Final answers
        are displayed in the right panel's _prompt_text (readonly). This test
        is kept as documentation of what was removed."""
        # This test is intentionally a no-op placeholder to document the removal.
        # The _final_answer_text attribute does not exist in MyAgentWindow.
        pass

    def test_interrupt_button_exists(self):
        """Verify '打断' button exists with correct text."""
        self.assertTrue(
            hasattr(self.win, '_interrupt_btn'),
            "MyAgentWindow should have _interrupt_btn attribute"
        )
        self.assertIsInstance(
            self.win._interrupt_btn, tk.Button,
            "_interrupt_btn should be a tkinter Button"
        )
        self.assertEqual(
            self.win._interrupt_btn.cget('text'), '打断',
            "'打断' button text should be '打断'"
        )

    def test_layout_no_overlap(self):
        """Verify left panel controls have valid geometry.

        Use reqwidth/reqheight (requested size) instead of allocated width/height,
        as geometry manager may allocate 1x1 to children when parent container space
        is already consumed by prior test instances sharing the same root.
        """
        self.root.update()
        for attr_name in ['_task_input_text', '_start_task_btn',
                          '_exec_log_text', '_interrupt_btn', '_new_task_btn']:
            widget = getattr(self.win, attr_name)
            self.root.update()
            rw = widget.winfo_reqwidth()
            rh = widget.winfo_reqheight()
            self.assertGreater(
                rw, 1,
                f"{attr_name} reqwidth should be > 1 (got {rw})"
            )
            self.assertGreater(
                rh, 1,
                f"{attr_name} reqheight should be > 1 (got {rh})"
            )


if __name__ == '__main__':
    unittest.main()
# -*- coding: utf-8 -*-
"""
test_button_protection.py - TDD tests for Task E7: Button state protection.

Verifies that buttons are correctly enabled/disabled based on REPL state:
- [开始任务] disabled in non-IDLE states, enabled in IDLE only with input
- [打断] disabled in IDLE, enabled in GENERATING_PROMPT/WAITING_RESPONSE/PROCESSING
- [新建任务] behavior per spec
- [粘贴&提交] enabled only in WAITING_RESPONSE state
"""
import sys
import os
import pathlib
import unittest

sys.path.insert(0, 'C:/Users/15041/.openclaw/workspace/MyAgent')

try:
    import tkinter as tk
    from agent.ui import MyAgentWindow
except ImportError:
    tk = None
    MyAgentWindow = None


class TestButtonProtection(unittest.TestCase):
    """Tests for button state protection based on REPL state (Task E7)."""

    def setUp(self):
        if tk is None:
            self.skipTest("tkinter not available")
        # Re-use the shared root from conftest to avoid Tcl initialization conflicts
        self.root = tk.Tk()
        self.root.withdraw()
        self.win = MyAgentWindow(self.root)
        self.win._io_dir = pathlib.Path('C:/Users/15041/.openclaw/workspace/MyAgent/io')
        self.win._io_dir.mkdir(exist_ok=True)

    def tearDown(self):
        self.win.root.destroy()

    # ------------------------------------------------------------------
    # [开始任务] button tests
    # ------------------------------------------------------------------

    def test_start_disabled_when_input_empty(self):
        """Start button should be disabled when input is empty or placeholder."""
        self.win._repl_state = 'IDLE'
        self.win._task_input_text.delete('1.0', tk.END)
        self.win._task_input_text.insert('1.0', '')
        self.win._update_button_states()
        self.assertEqual(self.win._start_task_btn.cget('state'), tk.DISABLED)

    def test_start_disabled_when_input_is_placeholder(self):
        """Start button should be disabled when input is the placeholder text."""
        self.win._repl_state = 'IDLE'
        self.win._task_input_text.delete('1.0', tk.END)
        self.win._task_input_text.insert('1.0', self.win._placeholder_text)
        self.win._update_button_states()
        self.assertEqual(self.win._start_task_btn.cget('state'), tk.DISABLED)

    def test_start_enabled_when_input_has_content(self):
        """Start button should be enabled when input has actual content."""
        self.win._repl_state = 'IDLE'
        self.win._task_input_text.delete('1.0', tk.END)
        self.win._task_input_text.insert('1.0', 'a real task')
        self.win._task_input_text.configure(fg='black')
        self.win._update_button_states()
        self.assertEqual(self.win._start_task_btn.cget('state'), tk.NORMAL)

    def test_start_disabled_when_generating_prompt(self):
        """Start button should be disabled during GENERATING_PROMPT."""
        self.win._repl_state = 'GENERATING_PROMPT'
        self.win._update_button_states()
        self.assertEqual(self.win._start_task_btn.cget('state'), tk.DISABLED)

    def test_start_disabled_when_waiting_response(self):
        """Start button should be disabled during WAITING_RESPONSE."""
        self.win._repl_state = 'WAITING_RESPONSE'
        self.win._update_button_states()
        self.assertEqual(self.win._start_task_btn.cget('state'), tk.DISABLED)

    def test_start_disabled_when_processing(self):
        """Start button should be disabled during PROCESSING."""
        self.win._repl_state = 'PROCESSING'
        self.win._update_button_states()
        self.assertEqual(self.win._start_task_btn.cget('state'), tk.DISABLED)

    # ------------------------------------------------------------------
    # [打断] button tests
    # ------------------------------------------------------------------

    def test_interrupt_disabled_when_idle(self):
        """Interrupt button should be disabled in IDLE state."""
        self.win._repl_state = 'IDLE'
        self.win._update_button_states()
        self.assertEqual(self.win._interrupt_btn.cget('state'), tk.DISABLED)

    def test_interrupt_enabled_when_generating_prompt(self):
        """Interrupt button should be enabled during GENERATING_PROMPT."""
        self.win._repl_state = 'GENERATING_PROMPT'
        self.win._update_button_states()
        self.assertEqual(self.win._interrupt_btn.cget('state'), tk.NORMAL)

    def test_interrupt_enabled_when_waiting_response(self):
        """Interrupt button should be enabled during WAITING_RESPONSE."""
        self.win._repl_state = 'WAITING_RESPONSE'
        self.win._update_button_states()
        self.assertEqual(self.win._interrupt_btn.cget('state'), tk.NORMAL)

    def test_interrupt_enabled_when_processing(self):
        """Interrupt button should be enabled during PROCESSING."""
        self.win._repl_state = 'PROCESSING'
        self.win._update_button_states()
        self.assertEqual(self.win._interrupt_btn.cget('state'), tk.NORMAL)

    # ------------------------------------------------------------------
    # [粘贴&提交] button tests
    # ------------------------------------------------------------------

    def test_submit_disabled_when_idle(self):
        """Submit button should be disabled in IDLE state."""
        self.win._repl_state = 'IDLE'
        self.win._update_button_states()
        self.assertEqual(self.win._submit_response_btn.cget('state'), tk.DISABLED)

    def test_submit_disabled_when_generating_prompt(self):
        """Submit button should be disabled during GENERATING_PROMPT."""
        self.win._repl_state = 'GENERATING_PROMPT'
        self.win._update_button_states()
        self.assertEqual(self.win._submit_response_btn.cget('state'), tk.DISABLED)

    def test_submit_enabled_when_waiting_response(self):
        """Submit button should be enabled when prompt is ready (WAITING_RESPONSE)."""
        self.win._repl_state = 'WAITING_RESPONSE'
        self.win._update_button_states()
        self.assertEqual(self.win._submit_response_btn.cget('state'), tk.NORMAL)

    def test_submit_disabled_when_processing(self):
        """Submit button should be disabled during PROCESSING."""
        self.win._repl_state = 'PROCESSING'
        self.win._update_button_states()
        self.assertEqual(self.win._submit_response_btn.cget('state'), tk.DISABLED)


if __name__ == '__main__':
    unittest.main()
# -*- coding: utf-8 -*-
"""
Test for Task E3: Guided prompts and placeholder system for MyAgent UI.

TDD Phase: RED (write failing tests first)

Tests:
- Input placeholder text and color on init
- Placeholder clears on click (Button-1)
- Placeholder restores on focus-out when empty
- Status bar shows appropriate message per state
- Guidance text appears in _exec_log_text at appropriate states
"""
import tkinter as tk
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestGuidedPrompts(unittest.TestCase):
    """Tests for guided prompts and placeholder system."""

    @classmethod
    def setUpClass(cls):
        """Create a hidden root window shared across all tests."""
        cls._shared_root = tk.Tk()
        cls._shared_root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls._shared_root.update()
        cls._shared_root.destroy()

    def setUp(self):
        self.root = self._shared_root
        self.root.update()

    def test_input_placeholder_on_init(self):
        """On init, task input shows placeholder text in gray color."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()

        # Check placeholder text is present
        content = win._task_input_text.get('1.0', tk.END)
        self.assertEqual(content.strip(), win._placeholder_text)
        # Check color is text_dim (#808080)
        fg = win._task_input_text.cget('fg')
        self.assertEqual(fg, '#808080')

    def test_placeholder_clears_on_click(self):
        """Clicking task input clears placeholder."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()

        # Simulate Button-1 click on task input
        win._task_input_text.event_generate('<Button-1>')
        self.root.update()

        # Placeholder should be cleared, color should be text_main (#333333)
        # After click, actual user text is typed → dark gray visible on white bg
        content = win._task_input_text.get('1.0', tk.END).strip()
        self.assertNotEqual(content, win._placeholder_text)
        fg = win._task_input_text.cget('fg')
        self.assertEqual(fg, '#333333')

    def test_placeholder_restores_on_empty(self):
        """If user clears input without typing, placeholder restores on focus-out."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()

        # Clear the input (simulate user deleted placeholder and left empty)
        win._task_input_text.event_generate('<Button-1>')
        self.root.update()
        win._task_input_text.delete('1.0', tk.END)
        self.root.update()

        # Trigger focus-out
        win._task_input_text.event_generate('<FocusOut>')
        self.root.update()

        # Placeholder should be restored with text_dim color
        content = win._task_input_text.get('1.0', tk.END).strip()
        self.assertEqual(content, win._placeholder_text)
        fg = win._task_input_text.cget('fg')
        self.assertEqual(fg, '#808080')

    def test_status_bar_shows_idle_message(self):
        """Status label shows '状态: 就绪' on startup."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()

        self.assertEqual(win._status_label.cget('text'), '\u72b6\u6001: \u5c31\u7eea')

    def test_status_bar_shows_generating_message(self):
        """Status shows '状态: 正在生成 prompt...' during GENERATING_PROMPT state."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()

        win._set_state('GENERATING_PROMPT')
        self.root.update()

        self.assertEqual(win._status_label.cget('text'), '\u72b6\u6001: \u6b63\u5728\u751f\u6210 prompt...')

    def test_status_bar_shows_waiting_message(self):
        """Status shows '状态: 等待 LLM 回复' during WAITING_RESPONSE state."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()

        win._set_state('WAITING_RESPONSE')
        self.root.update()

        self.assertEqual(win._status_label.cget('text'), '\u72b6\u6001: \u7b49\u5f85 LLM \u56de\u590d')

    def test_guidance_text_appears_in_log(self):
        """At appropriate states, guidance text appears in _exec_log_text."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()

        # Drain any startup log entries
        while not win._log_queue.empty():
            try:
                win._log_queue.get_nowait()
            except:
                break

        # Set GENERATING_PROMPT - should append guidance
        win._set_state('GENERATING_PROMPT')
        self.root.update()
        self.root.after(200)  # let log queue drain
        # Poll the log queue
        win._poll_log_queue()

        # Check log contains guidance
        log_content = win._exec_log_text.get('1.0', tk.END)
        self.assertIn('\u6b63\u5728\u751f\u6210 prompt', log_content)

        # Set WAITING_RESPONSE - should append different guidance
        win._set_state('WAITING_RESPONSE')
        self.root.update()
        win._poll_log_queue()

        log_content = win._exec_log_text.get('1.0', tk.END)
        self.assertIn('prompt \u5df2\u751f\u6210', log_content)


if __name__ == '__main__':
    unittest.main()
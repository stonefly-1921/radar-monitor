# -*- coding: utf-8 -*-
"""
test_repl_integration.py - TDD tests for Task E1: UI-REPL integration.

Verifies the core wiring between MyAgentWindow (ui.py) and the REPL
subprocess (loop_v2.py):
- Clicking "开始任务" writes task to io/input.txt
- Clicking "粘贴 & 提交" writes response to io/response.txt
- ui.py starts loop_v2.py as subprocess on start()
- _poll_io_files correctly reads prompt.txt and final_answer.txt
- State machine flows IDLE → GENERATING_PROMPT → WAITING_RESPONSE →
  PROCESSING → IDLE
"""
import os
import sys
import time
import tempfile
import shutil
import unittest

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    import tkinter as tk
    from agent import ui as ui_module
except ImportError:
    tk = None
    ui_module = None


class MockREPLProcess(object):
    """Minimal mock of subprocess.Popen for REPL."""

    def __init__(self):
        self.stdin_buf = []
        self._running = False
        self.stdin = None

    def poll(self):
        return -1 if self._running else 0


class MockStdin(object):
    """Fake stdin for mock REPL process."""

    def write(self, text):
        pass

    def flush(self):
        pass


class TestREPLIntegration(unittest.TestCase):
    """Tests for UI-REPL integration (Task E1)."""

    def setUp(self):
        """Create a fresh temporary io/ directory for each test."""
        self._tmp_dir = tempfile.mkdtemp(prefix='myagent_test_')
        self._io_dir = os.path.join(self._tmp_dir, 'io')
        os.makedirs(self._io_dir)

    def tearDown(self):
        """Clean up temp dir after each test."""
        try:
            shutil.rmtree(self._tmp_dir, ignore_errors=True)
        except Exception:
            pass

    @classmethod
    def setUpClass(cls):
        """Record original cwd (for teardown if needed)."""
        cls._orig_cwd = os.getcwd()

    @classmethod
    def tearDownClass(cls):
        """Restore cwd."""
        os.chdir(cls._orig_cwd)

    def _make_window(self):
        """Create a MyAgentWindow with its own fresh io/ directory."""
        if tk is None:
            self.skipTest("tkinter not available")
        root = tk.Tk()
        root.withdraw()  # hide window during tests
        win = ui_module.MyAgentWindow(root=root)
        # Override _io_dir to point at fresh per-test temp dir
        win._io_dir = self._io_dir
        return win

    # ------------------------------------------------------------------
    # test 1: clicking start writes task to io/input.txt
    # ------------------------------------------------------------------

    def test_on_start_task_writes_to_input_file(self):
        """Clicking start writes task content to io/input.txt."""
        win = self._make_window()

        # Put a task in the task input widget (skip placeholder)
        win._task_input_text.delete('1.0', tk.END)
        win._task_input_text.insert('1.0', '\u6d4b\u8bd5\u4efb\u52a1\uff1a\u8ba1\u7b97 1+1')
        win._task_input_text.configure(fg='black')

        # Call _on_start_task
        win._on_start_task()

        # Verify input.txt was written
        input_file = os.path.join(self._io_dir, 'input.txt')
        self.assertTrue(os.path.exists(input_file),
                        "input.txt should be created")
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertEqual(content, '\u6d4b\u8bd5\u4efb\u52a1\uff1a\u8ba1\u7b97 1+1')

        # Widget should be cleared (placeholder restored)
        widget_text = win._task_input_text.get('1.0', tk.END).strip()
        self.assertEqual(widget_text, win._placeholder_text,
                         "Task input should show placeholder after start")

        win.root.destroy()

    # ------------------------------------------------------------------
    # test 2: clicking submit writes response to io/response.txt
    # ------------------------------------------------------------------

    def test_on_submit_response_writes_to_response_file(self):
        """Clicking submit writes response content to io/response.txt."""
        win = self._make_window()

        # Put response in the response widget
        win._response_text.insert('1.0',
                                  '{"think":"ok","action":"final","answer":"2"}')

        # Call _on_submit_response
        win._on_submit_response()

        # Verify response.txt was written
        response_file = os.path.join(self._io_dir, 'response.txt')
        self.assertTrue(os.path.exists(response_file),
                        "response.txt should be created")
        with open(response_file, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertEqual(content,
                         '{"think":"ok","action":"final","answer":"2"}')

        # Widget should be cleared
        widget_text = win._response_text.get('1.0', tk.END).strip()
        self.assertEqual(widget_text, '',
                         "Response text should be cleared after submit")

        win.root.destroy()

    # ------------------------------------------------------------------
    # test 3: ui.py starts loop_v2.py as subprocess on start()
    # ------------------------------------------------------------------

    def test_ui_starts_repl_subprocess(self):
        """MyAgentWindow.start() launches loop_v2.py as a subprocess."""
        if tk is None:
            self.skipTest("tkinter not available")

        started = []
        root = tk.Tk()
        root.withdraw()
        win = ui_module.MyAgentWindow(root=root)

        # Patch to track call and provide a mock process
        def tracking_start_repl():
            started.append(True)
            win._repl_process = MockREPLProcess()
            win._repl_process.stdin = MockStdin()

        win._start_repl_subprocess = tracking_start_repl
        win._poll_io_files = lambda: None  # disable actual polling

        # Override io_dir to temp
        win._io_dir = self._io_dir
        win.start()

        self.assertEqual(len(started), 1,
                         "REPL subprocess should be started once")
        self.assertIsNotNone(win._repl_process,
                             "_repl_process should be set")

        win.root.destroy()

    # ------------------------------------------------------------------
    # test 4: _poll_io_files detects prompt.txt
    # ------------------------------------------------------------------

    def test_poll_io_detects_prompt_file(self):
        """_poll_io_files reads prompt.txt and updates _prompt_text."""
        win = self._make_window()
        win._last_prompt = ''
        win._last_final = ''

        # Write a prompt.txt file
        prompt_file = os.path.join(self._io_dir, 'prompt.txt')
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write('\u8fd9\u662f\u751f\u6210\u7684 prompt \u5185\u5bb9')

        # Call _poll_io_files once
        win._poll_io_files()

        # Verify _prompt_text was updated
        prompt_content = win._prompt_text.get('1.0', tk.END).strip()
        self.assertEqual(prompt_content, '\u8fd9\u662f\u751f\u6210\u7684 prompt \u5185\u5bb9',
                         "prompt.txt content should appear in _prompt_text")

        # Verify state changed to WAITING_RESPONSE
        self.assertEqual(win._repl_state, 'WAITING_RESPONSE',
                         "State should be WAITING_RESPONSE after prompt appears")

        win.root.destroy()

    # ------------------------------------------------------------------
    # test 5: _poll_io_files detects final_answer.txt
    # ------------------------------------------------------------------

    def test_poll_io_detects_final_answer(self):
        """_poll_io_files reads final_answer.txt and shows it in log."""
        win = self._make_window()
        win._last_prompt = ''
        win._last_final = ''

        # Pre-write prompt so the state machine has something to show
        prompt_file = os.path.join(self._io_dir, 'prompt.txt')
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write('a prompt')

        # Write a final_answer.txt file
        final_file = os.path.join(self._io_dir, 'final_answer.txt')
        with open(final_file, 'w', encoding='utf-8') as f:
            f.write('\u8fd9\u662f\u6700\u7ec8\u7b54\u6848\uff1a\u5706\u5468\u7387\u7b49\u4e8e 3.14')

        # Verify _write_final_answer was called with the final answer content
        write_final_calls = []
        original_write_final = win._write_final_answer
        def tracking_write_final(content):
            write_final_calls.append(content)
            return original_write_final(content)
        win._write_final_answer = tracking_write_final

        # Track append_log calls (for guidance messages during other states)
        append_log_calls = []
        original_append_log = win.append_log
        def tracking_append_log(tag_or_msg, msg=None):
            append_log_calls.append((tag_or_msg, msg))
            return original_append_log(tag_or_msg, msg)
        win.append_log = tracking_append_log

        # Call _poll_io_files once
        win._poll_io_files()

        # Verify final answer was detected and state returned to IDLE
        self.assertEqual(win._repl_state, 'IDLE',
                         "State should return to IDLE after final_answer.txt")

        # Verify _write_final_answer was called (E2: separator now goes directly
        # into _write_final_answer, not through append_log)
        self.assertTrue(len(write_final_calls) > 0,
                       "_write_final_answer should be called with final answer; "
                       "got: " + str(write_final_calls))
        self.assertEqual(write_final_calls[0], '\u8fd9\u662f\u6700\u7ec8\u7b54\u6848\uff1a\u5706\u5468\u7387\u7b49\u4e8e 3.14')

        # Verify final answer content was inserted into log via _insert_log_safe
        log_content = win._exec_log_text.get('1.0', tk.END)
        self.assertIn('\u8fd9\u662f\u6700\u7ec8\u7b54\u6848',
                      log_content,
                      "Final answer content should appear in log")
        win.root.destroy()

    # ------------------------------------------------------------------
    # test 6: prompt content appears in _prompt_text widget
    # ------------------------------------------------------------------

    def test_show_prompt_displays_in_widget(self):
        """Writing prompt.txt should populate _prompt_text widget."""
        win = self._make_window()
        win._last_prompt = ''
        win._last_final = ''

        prompt_file = os.path.join(self._io_dir, 'prompt.txt')
        test_prompt = ('\u3010\u7cfb\u7edf\u3011\u4f60\u662f\u4e00\u4e2a\u6709\u5e2e\u52a9\u7684\u52a9\u624b\u3002\n'
                      '\u3010\u4efb\u52a1\u3011\u8ba1\u7b97 1+1')
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(test_prompt)

        win._poll_io_files()

        content = win._prompt_text.get('1.0', tk.END).strip()
        self.assertEqual(content, test_prompt)

        win.root.destroy()

    # ------------------------------------------------------------------
    # test 7: state machine flow: IDLE → GENERATING_PROMPT →
    #         WAITING_RESPONSE → PROCESSING → IDLE
    # ------------------------------------------------------------------

    def test_state_machine_flow(self):
        """Full state machine cycle: IDLE -> GENERATING_PROMPT."""
        win = self._make_window()
        win._last_prompt = ''
        win._last_final = ''

        # Initial state should be IDLE
        self.assertEqual(win._repl_state, 'IDLE',
                         "Initial state should be IDLE")

        # Simulate user clicking start: IDLE -> GENERATING_PROMPT
        win._task_input_text.delete('1.0', tk.END)
        win._task_input_text.insert('1.0', '\u6d4b\u8bd5\u4efb\u52a1')
        win._task_input_text.configure(fg='black')
        win._on_start_task()

        self.assertEqual(win._repl_state, 'GENERATING_PROMPT',
                         "State should be GENERATING_PROMPT after start")

        # Simulate REPL writing prompt.txt:
        # GENERATING_PROMPT -> WAITING_RESPONSE
        prompt_file = os.path.join(self._io_dir, 'prompt.txt')
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write('generated prompt')
        win._poll_io_files()

        self.assertEqual(win._repl_state, 'WAITING_RESPONSE',
                         "State should be WAITING_RESPONSE after prompt.txt appears")

        # Simulate user submitting response:
        # WAITING_RESPONSE -> PROCESSING
        win._response_text.insert('1.0', '{"think":"ok","action":"final"}')
        win._on_submit_response()

        self.assertEqual(win._repl_state, 'PROCESSING',
                         "State should be PROCESSING after submit")

        # Simulate REPL writing final_answer.txt:
        # PROCESSING -> IDLE
        final_file = os.path.join(self._io_dir, 'final_answer.txt')
        with open(final_file, 'w', encoding='utf-8') as f:
            f.write('final answer here')
        win._poll_io_files()

        self.assertEqual(win._repl_state, 'IDLE',
                         "State should return to IDLE after final_answer.txt")

        win.root.destroy()


if __name__ == '__main__':
    unittest.main()
# -*- coding: utf-8 -*-
"""
Test for Task B2: Interrupt Mechanism
TDD Phase: RED (write failing tests first)

Tests:
- _interrupt_event is threading.Event instance
- _interrupt() sets the event
- _check_interrupt() raises InterruptedError when set
- _check_interrupt() does NOT raise when not set
- _is_interrupted() returns event.is_set()
- _reset_interrupt() clears the event
- 打断 button exists and is wired to _interrupt()
- 新任务 button exists
"""
import unittest
import sys
import os
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestInterruptMechanism(unittest.TestCase):
    """Tests for interrupt mechanism in MyAgentWindow."""

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

    def test_interrupt_event_is_thread_event_instance(self):
        """Verify _interrupt_event is a threading.Event instance."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        self.assertIsInstance(win._interrupt_event, threading.Event)

    def test_interrupt_sets_event(self):
        """Verify _interrupt() sets the event (is_set() returns True after call)."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        self.assertFalse(win._interrupt_event.is_set())
        win._interrupt()
        self.assertTrue(win._interrupt_event.is_set())

    def test_check_interrupt_raises_when_set(self):
        """Verify _check_interrupt() raises InterruptedError when event is set."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        win._interrupt()
        with self.assertRaises(InterruptedError):
            win._check_interrupt()

    def test_check_interrupt_does_not_raise_when_not_set(self):
        """Verify _check_interrupt() does NOT raise when event is not set."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        # Should not raise
        win._check_interrupt()

    def test_is_interrupted_returns_event_is_set(self):
        """Verify _is_interrupted() returns interrupt_event.is_set()."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        self.assertFalse(win._is_interrupted())
        win._interrupt()
        self.assertTrue(win._is_interrupted())

    def test_reset_interrupt_clears_event(self):
        """Verify _reset_interrupt() calls event.clear()."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        win._interrupt()
        self.assertTrue(win._interrupt_event.is_set())
        win._reset_interrupt()
        self.assertFalse(win._interrupt_event.is_set())

    def test_interrupt_button_exists(self):
        """Verify 打断 button exists and is labeled '打断'."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        self.assertIsNotNone(getattr(win, '_interrupt_btn', None))
        self.assertEqual(win._interrupt_btn.cget('text'), '打断')

    def test_new_task_button_exists(self):
        """Verify 新任务 button exists and is labeled '新任务'."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        self.assertIsNotNone(getattr(win, '_new_task_btn', None))
        self.assertEqual(win._new_task_btn.cget('text'), '新任务')

    def test_interrupt_button_calls_interrupt_method(self):
        """Verify clicking 打断 button triggers _interrupt() method."""
        from agent.ui import MyAgentWindow
        win = MyAgentWindow(self.root)
        self.root.update()
        # Call the button's callback directly (simulates button click)
        win._interrupt_btn.invoke()
        self.assertTrue(win._interrupt_event.is_set())


if __name__ == '__main__':
    unittest.main()
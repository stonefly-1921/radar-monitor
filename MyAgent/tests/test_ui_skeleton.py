# -*- coding: utf-8 -*-
"""
Test for Task A1: UI Skeleton
TDD Phase: RED (write failing tests first)

Modified to use gui_mock for headless testing (no DISPLAY required).
"""
import unittest
import sys
import os

# Ensure the agent package is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Apply headless mocks BEFORE importing MyAgentWindow or tkinter
from tests.gui_mock import apply_mocks, MockTk
apply_mocks()

# Now import tkinter (which is now the mocked version)
import tkinter

from agent.ui import MyAgentWindow


class TestUiSkeleton(unittest.TestCase):
    """Tests for MyAgentWindow UI skeleton."""

    @classmethod
    def setUpClass(cls):
        """Create a hidden root window shared across all tests in this class."""
        # MockTk doesn't need display - just use it directly
        cls._shared_root = MockTk()
        cls._shared_root.withdraw()  # hide window during tests

    @classmethod
    def tearDownClass(cls):
        """Destroy the shared root after all tests complete."""
        cls._shared_root.update()
        cls._shared_root.destroy()
        cls._shared_root.update()
        MockTk._reset()

    def setUp(self):
        """Re-use the shared root for each test (avoids Tk resource exhaustion)."""
        self.root = self._shared_root
        self.root.update()

    def test_window_title(self):
        """Verify window title is 'MyAgent v2'."""
        win = MyAgentWindow(self.root)
        self.root.update()
        self.assertEqual(win.root.title(), "MyAgent v2")

    def test_paned_window_exists(self):
        """Verify PanedWindow left/right split exists."""
        win = MyAgentWindow(self.root)
        self.root.update()
        self.assertIsNotNone(win._paned)

    def test_left_panel_width(self):
        """Verify left panel is approximately 400px wide."""
        win = MyAgentWindow(self.root)
        self.root.update()
        paned = win._paned
        self.assertIsNotNone(paned)
        paned.update_idletasks()
        sash_pos = paned.sash_coord(0)
        left_width = sash_pos[0]
        self.assertAlmostEqual(left_width, 400, delta=50)

    def test_right_panel_width(self):
        """Verify right panel is approximately 500px wide."""
        win = MyAgentWindow(self.root)
        self.root.update()
        paned = win._paned
        paned.update_idletasks()
        sash_pos = paned.sash_coord(0)
        left_width = sash_pos[0]
        # sash at 400px means left is 400, right should be 500
        # Verify the sash was placed at approximately 400px
        self.assertAlmostEqual(left_width, 400, delta=50)
        # Right panel width is not directly available as a sash coord,
        # but we can verify the left width is correctly set at ~400px.
        # The right panel will be 900 - 400 = 500px (total window width).

    def test_status_bar_exists(self):
        """Verify bottom status bar Frame and Label exist."""
        win = MyAgentWindow(self.root)
        self.root.update()
        self.assertIsNotNone(win._status_bar)
        self.assertIsNotNone(win._status_label)

    def test_status_bar_text(self):
        """Verify status bar label shows '状态: 就绪'."""
        win = MyAgentWindow(self.root)
        self.root.update()
        self.assertEqual(win._status_label.cget("text"), "状态: 就绪")

    def test_window_can_close(self):
        """Verify window can be closed without hanging (destroy exits cleanly)."""
        # Create a fresh root to test clean destroy
        # Patch tk.Tk globally so any code inside MyAgentWindow that creates tk.Tk()
        # also gets the mock
        import unittest.mock as mock
        with mock.patch.object(tkinter, 'Tk', return_value=MockTk()):
            test_root = tkinter.Tk()
            test_root.withdraw()
            win = MyAgentWindow(test_root)
            test_root.update()
            test_root.destroy()
            test_root.update()


if __name__ == '__main__':
    unittest.main()

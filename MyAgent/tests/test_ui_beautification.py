# -*- coding: utf-8 -*-
"""
MyAgent Tkinter UI - Task E4: UI Beautification Tests

Tests verify the dark theme color palette is correctly applied:
- Window background: #1e1e1e (dark gray)
- Panel background: #252526 (slightly lighter)
- Button background: #0e639c (accent deep blue)
- Status bar text: dimmed color

TDD RED phase: write failing tests first.
"""
import unittest
import tkinter as tk
import sys
import os

# Ensure MyAgent package in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agent.ui import MyAgentWindow


def hex_to_rgb_16bit(hex_color):
    """Convert '#1e1e1e' format to 16-bit RGB tuple (e.g., (7710, 7710, 7710))."""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    # tkinter winfo_rgb returns 16-bit values (0-65535)
    return (r * 257, g * 257, b * 257)


class TestUiBeautification(unittest.TestCase):
    """Tests for UI beautification - dark theme color palette."""

    @classmethod
    def setUpClass(cls):
        """Create a visible root window shared across all tests."""
        cls._shared_root = tk.Tk()
        # Do NOT withdraw - geometry manager needs to allocate widget space

    @classmethod
    def tearDownClass(cls):
        """Destroy the shared root after all tests complete."""
        cls._shared_root.update()
        cls._shared_root.destroy()

    def setUp(self):
        """Re-use shared root for each test."""
        self.root = self._shared_root
        self.root.update()
        from agent.ui import MyAgentWindow
        self.win = MyAgentWindow(root=self.root)
        self.root.update()

    def test_window_has_dark_background(self):
        """Verify window root background is dark (#1e1e1e)."""
        bg_color = self.win.root.cget('bg')
        bg_rgb = self.win.root.winfo_rgb(bg_color)
        expected_rgb = hex_to_rgb_16bit('#1e1e1e')
        self.assertEqual(
            bg_rgb, expected_rgb,
            "Window background should be #1e1e1e (dark), got {} (color={})".format(bg_rgb, bg_color)
        )

    def test_panels_have_correct_background(self):
        """Verify left and right panels have #252526 background."""
        expected_rgb = hex_to_rgb_16bit('#252526')

        left_color = self.win._left_panel.cget('bg')
        left_bg = self.win._left_panel.winfo_rgb(left_color)
        self.assertEqual(
            left_bg, expected_rgb,
            "Left panel background should be #252526, got {} (color={})".format(left_bg, left_color)
        )

        right_color = self.win._right_panel.cget('bg')
        right_bg = self.win._right_panel.winfo_rgb(right_color)
        self.assertEqual(
            right_bg, expected_rgb,
            "Right panel background should be #252526, got {} (color={})".format(right_bg, right_color)
        )

    def test_buttons_have_blue_background(self):
        """Verify primary buttons use accent_deep color (#0e639c)."""
        expected_rgb = hex_to_rgb_16bit('#0e639c')

        btn_bg_color = self.win._start_task_btn.cget('bg')
        start_btn_bg = self.win._start_task_btn.winfo_rgb(btn_bg_color)
        self.assertEqual(
            start_btn_bg, expected_rgb,
            "Start task button background should be #0e639c, got {} (color={})".format(start_btn_bg, btn_bg_color)
        )

    def test_status_bar_label_text_color_dimmed(self):
        """Verify status label uses dimmed text color (#808080)."""
        expected_rgb = hex_to_rgb_16bit('#808080')
        fg_color = self.win._status_label.cget('fg')
        fg_rgb = self.win._status_label.winfo_rgb(fg_color)
        self.assertEqual(
            fg_rgb, expected_rgb,
            "Status label foreground should be #808080 (dimmed), got {} (color={})".format(fg_rgb, fg_color)
        )

    def test_window_title_updated(self):
        """Verify window title is 'MyAgent v2.1'."""
        self.assertEqual(self.win.root.title(), "MyAgent v2.1")

    def test_window_default_size(self):
        """Verify window default size is 1200x800."""
        geom = self.win.root.geometry()
        # geometry returns like "1200x800+..."
        size_part = geom.split('+')[0]
        self.assertEqual(size_part, "1200x800")

    def test_start_task_button_white_text(self):
        """Verify start task button has white foreground text."""
        fg_color = self.win._start_task_btn.cget('fg')
        fg_rgb = self.win._start_task_btn.winfo_rgb(fg_color)
        expected_white = hex_to_rgb_16bit('#ffffff')
        self.assertEqual(
            fg_rgb, expected_white,
            "Start task button text should be white, got {} (color={})".format(fg_rgb, fg_color)
        )

    def test_exec_log_text_has_dark_background(self):
        """Verify execution log text widget has dark background (#1e1e1e)."""
        expected_rgb = hex_to_rgb_16bit('#1e1e1e')
        bg_color = self.win._exec_log_text.cget('bg')
        bg_rgb = self.win._exec_log_text.winfo_rgb(bg_color)
        self.assertEqual(
            bg_rgb, expected_rgb,
            "Exec log text background should be #1e1e1e, got {} (color={})".format(bg_rgb, bg_color)
        )

    def test_exec_log_text_has_light_foreground(self):
        """Verify execution log text widget has light foreground (#d4d4d4)."""
        expected_rgb = hex_to_rgb_16bit('#d4d4d4')
        fg_color = self.win._exec_log_text.cget('fg')
        fg_rgb = self.win._exec_log_text.winfo_rgb(fg_color)
        self.assertEqual(
            fg_rgb, expected_rgb,
            "Exec log text foreground should be #d4d4d4, got {} (color={})".format(fg_rgb, fg_color)
        )


if __name__ == '__main__':
    unittest.main()
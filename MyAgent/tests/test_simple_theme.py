# -*- coding: utf-8 -*-
"""
Tests for Task E5: Simple Clean Light Theme

Verifies:
- Window background is white
- Buttons are simple gray (#f0f0f0), not blue
- Log text is black (no colorful tags)
- Window title is "MyAgent v2" (not v2.1)
"""
import unittest
import sys
import os
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.ui import MyAgentWindow


class TestSimpleLightTheme(unittest.TestCase):
    """Test simple clean light theme for MyAgent UI."""

    @classmethod
    def setUpClass(cls):
        """Create hidden root for all tests."""
        cls._root = tk.Tk()
        cls._root.withdraw()

    @classmethod
    def tearDownClass(cls):
        """Destroy root after all tests."""
        cls._root.destroy()

    def setUp(self):
        """Create fresh window for each test."""
        self.win = MyAgentWindow(root=self._root)

    def test_window_background_is_white(self):
        """Window background should be white (#ffffff) or very light gray (#f5f5f5)."""
        bg = self.win.root.cget('bg')
        allowed = ['#ffffff', '#f5f5f5', 'white', 'snow', 'ghost white', 'floral white']
        self.assertIn(bg.lower(), allowed,
            "Window bg is '{}', expected white or very light gray".format(bg))

    def test_panels_are_light_gray(self):
        """Panel background should be light gray (#f0f0f0 or #e8e8e8)."""
        panel_bg = self.win._left_panel.cget('bg')
        allowed = ['#f0f0f0', '#e8e8e8', '#f5f5f5']
        self.assertIn(panel_bg.lower(), allowed,
            "Panel bg is '{}', expected light gray".format(panel_bg))

    def test_buttons_are_simple_gray(self):
        """Buttons should be simple gray (#f0f0f0), NOT blue (#0078d4)."""
        btn = self.win._start_task_btn
        bg = btn.cget('bg').lower()
        blue_variants = ['#0078d4', '#106ebe', '#0e639c', 'blue', '#0000ff', '#000080']
        self.assertNotIn(bg, blue_variants,
            "Button bg is '{}' (blue) - should be simple gray".format(bg))
        # Should be light gray
        gray_variants = ['#f0f0f0', '#e8e8e8', '#e0e0e0', '#d0d0d0', '#cccccc', 'gray', 'grey']
        self.assertIn(bg, gray_variants,
            "Button bg is '{}', expected simple gray".format(bg))

    def test_button_text_is_dark_gray(self):
        """Button foreground should be dark gray (#333333), not white."""
        btn = self.win._start_task_btn
        fg = btn.cget('fg').lower()
        self.assertIn(fg, ['#333333', '#222222', '#444444', 'dark gray', 'darkgrey', '#333'],
            "Button fg is '{}', expected dark gray".format(fg))

    def test_buttons_use_flat_style(self):
        """Buttons should use flat relief style."""
        btn = self.win._start_task_btn
        relief = btn.cget('relief')
        self.assertEqual(relief, tk.FLAT,
            "Button relief is '{}', expected FLAT".format(relief))

    def test_interrupt_button_is_gray(self):
        """Interrupt button should also be simple gray."""
        btn = self.win._interrupt_btn
        bg = btn.cget('bg').lower()
        blue_variants = ['#0078d4', '#106ebe', '#0e639c', 'blue', '#0000ff']
        self.assertNotIn(bg, blue_variants,
            "Interrupt button bg is '{}' (blue)".format(bg))

    def test_submit_button_is_gray(self):
        """Submit response button should be simple gray."""
        btn = self.win._submit_response_btn
        bg = btn.cget('bg').lower()
        blue_variants = ['#0078d4', '#106ebe', '#0e639c', 'blue', '#0000ff']
        self.assertNotIn(bg, blue_variants,
            "Submit button bg is '{}' (blue)".format(bg))

    def test_log_text_is_black(self):
        """Log text should be black on white, no colorful tags."""
        log_text = self.win._exec_log_text
        fg = log_text.cget('fg').lower()
        allowed = ['#000000', '#000', 'black', '#111111', '#222222', '#333333']
        self.assertIn(fg, allowed,
            "Log fg is '{}', expected black".format(fg))
        bg = log_text.cget('bg').lower()
        self.assertIn(bg, ['#ffffff', 'white', '#fafafa'],
            "Log bg is '{}', expected white".format(bg))

    def test_window_title_is_myagent_v2(self):
        """Window title should be 'MyAgent v2' not 'MyAgent v2.1'."""
        title = self.win.root.title()
        self.assertEqual(title, "MyAgent v2",
            "Window title is '{}', expected 'MyAgent v2'".format(title))

    def test_status_bar_is_light_blue(self):
        """Status bar background should be light blue (#e8f4fd)."""
        status_bg = self.win._status_bar.cget('bg')
        self.assertIn(status_bg.lower(), ['#e8f4fd', '#dbeeff', '#e0f0ff'],
            "Status bar bg is '{}', expected light blue".format(status_bg))

    def test_status_bar_text_is_dark(self):
        """Status bar text should be dark gray, not white."""
        fg = self.win._status_label.cget('fg').lower()
        self.assertIn(fg, ['#333333', '#222222', '#444444', 'dark gray', 'darkgrey'],
            "Status label fg is '{}', expected dark gray".format(fg))

    def test_labels_are_dark_gray(self):
        """Labels should have dark gray text."""
        # Get first label in console panel
        labels = self.win._left_panel.winfo_children()
        for child in labels:
            if isinstance(child, tk.Label):
                fg = child.cget('fg').lower()
                self.assertIn(fg, ['#333333', '#222222', '#444444', 'dark gray', 'darkgrey', '#000000', 'black'],
                    "Label fg is '{}', expected dark".format(fg))
                break

    def test_input_text_has_white_background(self):
        """Task input text widget should have white background."""
        bg = self.win._task_input_text.cget('bg').lower()
        self.assertIn(bg, ['#ffffff', 'white'],
            "Input text bg is '{}', expected white".format(bg))

    def test_input_text_has_black_text(self):
        """Task input text widget should have dark text."""
        fg = self.win._task_input_text.cget('fg').lower()
        self.assertIn(fg, ['#000000', '#000', 'black', '#111111', '#222222', '#333333', '#808080'],
            "Input text fg is '{}', expected dark".format(fg))


if __name__ == '__main__':
    unittest.main()
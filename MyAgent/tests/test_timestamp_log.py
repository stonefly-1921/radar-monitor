# -*- coding: utf-8 -*-
"""
Test for Task B3: timestamped log markers
TDD Phase: RED (write failing tests first)

Tests _log_message(type, msg) method that formats and inserts timestamped entry.
Format: HH:MM:SS.mmm  [TYPE]  message
TYPE categories: USER / AGENT / TOOL / SYSTEM / ERROR
"""
import unittest
import sys
import os
import re
import queue
import threading
import time
import tkinter as tk

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestTimestampLog(unittest.TestCase):
    """Tests for timestamped log entries in MyAgent UI."""

    @classmethod
    def setUpClass(cls):
        cls._shared_root = tk.Tk()
        cls._shared_root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls._shared_root.update()
        cls._shared_root.destroy()

    def setUp(self):
        self.root = self._shared_root
        self.root.update()
        from agent.ui import MyAgentWindow
        self.win = MyAgentWindow(self.root)
        self.root.update()

    def _clear_log(self):
        """Helper to clear exec log text."""
        log_text = self.win._exec_log_text
        log_text.configure(state=tk.NORMAL)
        log_text.delete('1.0', tk.END)
        log_text.configure(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # RED Phase tests: these must FAIL before implementation
    # ------------------------------------------------------------------

    def test_log_message_method_exists(self):
        """Verify _log_message(type, msg) method exists on window."""
        self.assertTrue(hasattr(self.win, '_log_message'))
        self.assertTrue(callable(self.win._log_message))

    def test_format_log_returns_timestamp_format(self):
        """Verify _log_message returns string matching HH:MM:SS.mmm pattern."""
        result = self.win._log_message("USER", "hello")
        # Should match HH:MM:SS.mmm  [TYPE]  message
        self.assertIsInstance(result, str)
        timestamp_pattern = r'^\d{2}:\d{2}:\d{2}\.\d{3}  \[USER\]  hello$'
        self.assertIsNotNone(re.match(timestamp_pattern, result),
                             f"Expected format HH:MM:SS.mmm  [TYPE]  message, got: {result}")

    def test_timestamp_format_matches_hhmmssmmm(self):
        """Verify timestamp portion matches HH:MM:SS.mmm (e.g. 14:23:05.012)."""
        result = self.win._log_message("TOOL", "test")
        # Extract timestamp part (first 12 chars)
        ts_part = result[:12]
        ts_pattern = r'^\d{2}:\d{2}:\d{2}\.\d{3}$'
        self.assertIsNotNone(re.match(ts_pattern, ts_part),
                             f"Timestamp {ts_part} doesn't match HH:MM:SS.mmm")

    def test_type_prefix_appears_in_log(self):
        """Verify type prefix [TYPE] appears in formatted log entry."""
        result = self.win._log_message("AGENT", "thinking...")
        self.assertIn("[AGENT]", result)

    def test_all_supported_type_categories(self):
        """Verify all supported TYPE categories: USER/AGENT/TOOL/SYSTEM/ERROR."""
        types = ["USER", "AGENT", "TOOL", "SYSTEM", "ERROR"]
        for t in types:
            result = self.win._log_message(t, "msg")
            self.assertIn(f"[{t}]", result,
                          f"Type {t} not found in result: {result}")

    def test_separator_format_two_spaces(self):
        """Verify separator format: HH:MM:SS.mmm  [TYPE]  message (two spaces around brackets)."""
        result = self.win._log_message("SYSTEM", "boot")
        # Check exactly two spaces on each side of [TYPE]
        self.assertTrue(re.search(r'\d{2}:\d{2}:\d{2}\.\d{3}  \[SYSTEM\]  ', result),
                        f"Separator format wrong in: {result}")

    def test_append_log_with_type_adds_timestamp(self):
        """Verify append_log(tag, msg) adds formatted timestamped entry to queue."""
        self.assertTrue(hasattr(self.win, 'append_log'))
        self.win.append_log("TOOL", "file read")
        try:
            entry = self.win._log_queue.get_nowait()
        except queue.Empty:
            self.fail("append_log did not put entry in queue")

        # Entry must be a formatted string with timestamp and type
        self.assertIsInstance(entry, str)
        self.assertIn("[TOOL]", entry)
        ts_pattern = r'^\d{2}:\d{2}:\d{2}\.\d{3}  \[TOOL\]  file read$'
        self.assertIsNotNone(re.match(ts_pattern, entry),
                             f"append_log entry format wrong: {entry}")

    def test_multiple_entries_have_ascending_timestamps(self):
        """Verify multiple log entries have ascending timestamps (within resolution)."""
        log_text = self.win._exec_log_text
        self._clear_log()

        entries = [("USER", "first"), ("AGENT", "second"), ("TOOL", "third")]
        for tag, msg in entries:
            self.win.append_log(tag, msg)

        # Poll the queue
        for _ in range(20):
            self.win._poll_log_queue()
        self.root.update()

        log_text.configure(state=tk.NORMAL)
        content = log_text.get('1.0', tk.END)
        log_text.configure(state=tk.DISABLED)

        # Extract all timestamp strings
        timestamps = re.findall(r'\d{2}:\d{2}:\d{2}\.\d{3}', content)
        self.assertGreaterEqual(len(timestamps), 3,
                               f"Expected at least 3 timestamps, got: {timestamps}")

        # Each timestamp should be parseable and ascending (allowing same-timestamp)
        for i in range(len(timestamps) - 1):
            self.assertLessEqual(timestamps[i], timestamps[i + 1],
                                f"Timestamps not ascending: {timestamps[i]} -> {timestamps[i + 1]}")

    def test_log_insert_includes_timestamp_in_text(self):
        """Verify log entry inserted into Text widget includes timestamp prefix."""
        log_text = self.win._exec_log_text
        self._clear_log()

        self.win.append_log("ERROR", "something failed")
        self.win._poll_log_queue()
        self.root.update()

        log_text.configure(state=tk.NORMAL)
        content = log_text.get('1.0', tk.END)
        log_text.configure(state=tk.DISABLED)

        # Should contain a properly formatted timestamped entry
        self.assertIn("[ERROR]", content)
        ts_match = re.search(r'\d{2}:\d{2}:\d{2}\.\d{3}', content)
        self.assertIsNotNone(ts_match, f"No timestamp found in: {content}")

    def test_log_message_empty_msg_handled(self):
        """Verify _log_message handles empty message gracefully."""
        result = self.win._log_message("SYSTEM", "")
        self.assertIsInstance(result, str)
        self.assertIn("[SYSTEM]", result)
        # Should still have timestamp
        ts_pattern = r'^\d{2}:\d{2}:\d{2}\.\d{3}  \[SYSTEM\]  $'
        self.assertIsNotNone(re.match(ts_pattern, result),
                             f"Empty msg format wrong: {result}")


if __name__ == '__main__':
    unittest.main()
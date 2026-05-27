# -*- coding: utf-8 -*-
"""
conftest.py - Shared pytest fixtures for tkinter-based tests.

Provides a shared hidden Tk root that won't conflict between tests,
and improves isolation for tests that create/destroy many windows.
"""
import pytest
import sys
import os

# Ensure MyAgent on path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(scope="session")
def tk_shared_root():
    """Provide a session-scoped hidden Tk root, created once."""
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    yield root
    try:
        root.update()
        root.destroy()
    except Exception:
        pass


@pytest.fixture
def tk_root(tk_shared_root):
    """Per-test fixture that returns the shared root and updates it."""
    import tkinter as tk
    # Each test gets the shared root but we update it for this test
    tk_shared_root.update()
    return tk_shared_root
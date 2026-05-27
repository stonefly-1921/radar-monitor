# -*- coding: utf-8 -*-
"""
gui_mock/__init__.py - Mock tkinter components for headless GUI testing.

This module provides mock tkinter classes that subclass real tkinter widgets
(so isinstance checks pass) but suppress Tk initialization, allowing tests
to run in a headless environment without DISPLAY.

Usage in tests:
    from tests.gui_mock import MockTk, MockText, MockButton

    # Patch tkinter before importing MyAgentWindow
    import tkinter
    tkinter.Tk = MockTk
    tkinter.Text = MockText
    tkinter.Button = MockButton
    tkinter.Label = MockLabel
    tkinter.Frame = MockFrame
    tkinter.PanedWindow = MockPanedWindow
    tkinter.Scrollbar = MockScrollbar

    from agent.ui import MyAgentWindow
    # ... tests ...

"""
from __future__ import absolute_import

import sys
import os

# Add project root to path so we can import if needed
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

__all__ = [
    'MockTk',
    'MockText',
    'MockButton',
    'MockLabel',
    'MockFrame',
    'MockPanedWindow',
    'MockScrollbar',
    'apply_mocks',
    'setup_headless',
]

# -----------------------------------------------------------------------
# Lazy tkinter import with initialization suppression
# -----------------------------------------------------------------------

_tkinter_module = None

def _get_tkinter():
    """Lazily import tkinter, setting TKINTER_DONT_WAIT_FOR_DISPLAY to prevent hangs."""
    global _tkinter_module
    if _tkinter_module is None:
        os.environ.setdefault('TKINTER_DONT_WAIT_FOR_DISPLAY', '1')
        _tkinter_module = __import__('tkinter')
    return _tkinter_module


# -----------------------------------------------------------------------
# MockTk - Suppresses __init__ to avoid Tcl/Tk display requirement
# -----------------------------------------------------------------------

class _MockBase(object):
    """Common attributes shared by all mock widgets."""
    _mock_children = None
    _mock_config = None

    def __init__(self, *args, **kwargs):
        # Don't call super().__init__ - we don't have a Tk master
        self._mock_children = []
        self._mock_config = {}
        self._mock_attrs = dict(kwargs)
        # Capture geometry method results
        self._winfo_x = 0
        self._winfo_y = 0
        self._winfo_width = 1
        self._winfo_height = 1
        self._winfo_reqwidth = 100
        self._winfo_reqheight = 30
        # Pack propagation flag
        self._propagate = True

    def __repr__(self):
        return "<{}: {}>".format(self.__class__.__name__, id(self))

    # Base configure - all mocks call this
    def configure(self, **kwargs):
        self._mock_attrs.update(kwargs)

    def config(self, **kwargs):
        return self.configure(**kwargs)

    # Geometry info stubs
    def winfo_x(self): return self._winfo_x
    def winfo_y(self): return self._winfo_y
    def winfo_width(self): return self._winfo_width
    def winfo_height(self): return self._winfo_height
    def winfo_reqwidth(self): return self._winfo_reqwidth
    def winfo_reqheight(self): return self._winfo_reqheight
    def winfo_exists(self): return 1
    def winfo_ismapped(self): return 1
    def update_idletasks(self): pass
    def update(self): pass

    # Tk geometry methods (stubbed)
    def pack(self, *args, **kwargs): return None
    def grid(self, *args, **kwargs): return None
    def place(self, *args, **kwargs): return None
    def pack_propagate(self, flag=None):
        """Set or get pack propagation (whether pack affects widget size)."""
        if flag is None:
            return self._propagate
        self._propagate = flag
        return None
    def propagate(self, flag=None):
        return self.pack_propagate(flag)

    # Widget identity checks (subclasses override for proper isinstance)
    @classmethod
    def __subclasshook__(cls, C):
        return NotImplemented


class MockTk(_MockBase):
    """Mock Tk root that bypasses Tcl/Tk initialization.

    Instead of creating a real Tk instance (which requires a display),
    this stores attributes that tests access but doesn't initialize the
    underlying Tcl interpreter.
    """
    _instances = []

    def __init__(self, **kwargs):
        super(MockTk, self).__init__(**kwargs)
        MockTk._instances.append(self)
        self._mock_children = []
        self.title_value = kwargs.get('title', '')
        self.geometry_value = kwargs.get('geometry', '800x600')
        self._after_callbacks = {}

    def title(self, *args):
        if args:
            self.title_value = args[0]
        return self.title_value

    def geometry(self, *args):
        if args:
            self.geometry_value = args[0]
        return self.geometry_value

    def minsize(self, *args): pass
    def maxsize(self, *args): pass

    def configure(self, **kwargs):
        self._mock_attrs.update(kwargs)
        bg = kwargs.get('bg', None) or kwargs.get('background', None)
        if bg:
            self._mock_config['bg'] = bg

    def config(self, **kwargs):
        return self.configure(**kwargs)

    def withdraw(self): pass
    def deiconify(self): pass
    def destroy(self):
        # Remove from instances list
        if self in MockTk._instances:
            MockTk._instances.remove(self)

    def mainloop(self, *args, **kwargs):
        # No-op for tests - real tests don't call this
        pass

    def quit(self): pass

    def clipboard_clear(self): pass
    def clipboard_append(self, *args, **kwargs): pass

    def after(self, ms, callback=None, *args):
        """Store callback for later execution (not actually run in mock).
        
        Supports both:
        - root.after(ms, callback)   -> schedule callback
        - root.after(ms)            -> no-op sleep (real Tk does nothing)
        """
        if callback is None:
            return None  # no-op sleep
        key = id(callback)
        self._after_callbacks[key] = (callback, args)
        return key

    def after_cancel(self, key): pass

    @classmethod
    def _reset(cls):
        """Reset all MockTk instances (for test isolation)."""
        cls._instances.clear()


# -----------------------------------------------------------------------
# Widget mocks that pass isinstance() checks against real tkinter classes
# -----------------------------------------------------------------------

def _make_mock_class(mock_name, real_class_path):
    """Factory to create a mock widget class that subclasses the real tkinter class.

    We subclass the real class but bypass __init__ so no display is needed.
    This makes isinstance(widget, tk.Text) return True.
    """
    try:
        tk = _get_tkinter()
        parts = real_class_path.split('.')
        real_class = tk
        for part in parts:
            real_class = getattr(real_class, part)
    except Exception:
        # Fallback: create a class that claims to be the tkinter type
        real_class = object

    class _MockWidget(_MockBase):
        _real_class = real_class

        def __init__(self, master=None, **kwargs):
            super(_MockWidget, self).__init__(**kwargs)
            if master is not None:
                # Track parent-child relationship
                self._master = master
                if hasattr(master, '_mock_children'):
                    master._mock_children.append(self)
            else:
                self._master = None
            self._mock_attrs.update(kwargs)
            self._state = 'normal'
            self._text = ''
            self._fg = 'black'
            self._bg = 'white'

        @classmethod
        def __subclasshook__(cls, C):
            return isinstance(C, type) and issubclass(C, real_class)

        def cget(self, key):
            return self._mock_attrs.get(key, '')

        def config(self, **kwargs):
            return self.configure(**kwargs)

        def configure(self, **kwargs):
            self._mock_attrs.update(kwargs)
            for k, v in kwargs.items():
                if k == 'state':
                    self._state = v
                elif k == 'text':
                    self._text = v
                elif k in ('fg', 'foreground'):
                    self._fg = v
                elif k in ('bg', 'background'):
                    self._bg = v

        def keys(self):
            return list(self._mock_attrs.keys())

    _MockWidget.__name__ = mock_name
    _MockWidget.__qualname__ = mock_name
    return _MockWidget


MockFrame = _make_mock_class('MockFrame', 'Frame')
MockLabel = _make_mock_class('MockLabel', 'Label')


class MockText(_make_mock_class('MockText', 'Text')):
    """Mock Text widget that supports insert/delete/get operations."""

    def __init__(self, master=None, **kwargs):
        # Skip real tkinter.Text.__init__ (requires Tk master)
        _MockBase.__init__(self, master, **kwargs)
        self._master = master
        if master is not None and hasattr(master, '_mock_children'):
            master._mock_children.append(self)
        self._mock_attrs.update(kwargs)
        self._state = kwargs.get('state', 'normal')
        self._content = ''
        self._fg = kwargs.get('fg', 'black')
        self._bg = kwargs.get('bg', 'white')
        self._event_bindings = {}   # event_type -> list of callbacks

    def bind(self, sequence, func, add=None):
        """Bind event handler to this widget. add is ignored (always adds)."""
        if sequence not in self._event_bindings:
            self._event_bindings[sequence] = []
        self._event_bindings[sequence].append(func)

    def event_generate(self, sequence, **kw):
        """Generate an event, triggering bound handlers."""
        # Look up bindings for this event type (e.g., '<Button-1>', '<FocusIn>')
        # Store last event for potential inspection
        self._last_event = sequence
        cbs = self._event_bindings.get(sequence, [])
        for cb in cbs:
            cb(kw) if kw else cb(None)

    def yview(self, *args):
        """Text scroll callback - no-op mock."""
        return None

    def see(self, index):
        """Text widget see method - no-op mock."""
        return None

    def insert(self, index, text):
        if index == '1.0':
            self._content = text
        elif index == tk.END if 'tk' in dir() else 'end':
            self._content += text
        else:
            self._content += text

    def delete(self, index1, index2=None):
        if index2 is None:
            self._content = ''
        else:
            self._content = ''

    def get(self, index1, index2=None):
        if index2 is None:
            return self._content
        return self._content

    def configure(self, **kwargs):
        _MockBase.configure(self, **kwargs)
        if 'state' in kwargs:
            self._state = kwargs['state']
        if 'fg' in kwargs:
            self._fg = kwargs['fg']
        if 'bg' in kwargs:
            self._bg = kwargs['bg']

    def cget(self, key):
        if key == 'state':
            return self._state
        if key == 'fg':
            return self._fg
        if key == 'bg':
            return self._bg
        if key == 'text':
            return self._text
        return self._mock_attrs.get(key, '')

    def index(self, index):
        """Return line.column string for given index. 'end' returns last line."""
        if index == 'end':
            lines = self._content.split('\n')
            return f"{len(lines)}.0"
        return str(index)


class MockButton(_make_mock_class('MockButton', 'Button')):
    """Mock Button widget that tracks state and command."""

    def __init__(self, master=None, **kwargs):
        _MockBase.__init__(self, master, **kwargs)
        self._master = master
        if master is not None and hasattr(master, '_mock_children'):
            master._mock_children.append(self)
        self._mock_attrs.update(kwargs)
        self._state = kwargs.get('state', 'normal')
        self._text = kwargs.get('text', '')
        self._command = kwargs.get('command', None)
        self._fg = kwargs.get('fg', 'black')
        self._bg = kwargs.get('bg', 'white')

    def configure(self, **kwargs):
        _MockBase.configure(self, **kwargs)
        if 'state' in kwargs:
            self._state = kwargs['state']
        if 'text' in kwargs:
            self._text = kwargs['text']
        if 'command' in kwargs:
            self._command = kwargs['command']

    def config(self, **kwargs):
        return self.configure(**kwargs)

    def cget(self, key):
        if key == 'state':
            return self._state
        if key == 'text':
            return self._text
        if key == 'command':
            return self._command
        if key == 'fg':
            return self._fg
        if key == 'bg':
            return self._bg
        return self._mock_attrs.get(key, '')

    def invoke(self):
        if self._command and self._state != 'disabled':
            return self._command()


class MockPanedWindow(_make_mock_class('MockPanedWindow', 'PanedWindow')):
    """Mock PanedWindow that tracks sash position."""

    def __init__(self, master=None, **kwargs):
        _MockBase.__init__(self, master, **kwargs)
        self._master = master
        if master is not None and hasattr(master, '_mock_children'):
            master._mock_children.append(self)
        self._mock_attrs.update(kwargs)
        self._orient = kwargs.get('orient', 'horizontal')
        self._children = []
        self._sash_positions = {0: 400}
        self._winfo_width = 900
        self._winfo_height = 600

    def add(self, child, **kwargs):
        self._children.append(child)

    def forget(self, child): pass

    def sash_place(self, index, x, y):
        self._sash_positions[index] = x

    def sash_coord(self, index):
        x = self._sash_positions.get(index, 400)
        return (x, 0)

    def pack(self, *args, **kwargs): pass
    def update_idletasks(self): pass

    def winfo_width(self):
        return self._winfo_width

    def configure(self, **kwargs):
        _MockBase.configure(self, **kwargs)


class MockScrollbar(_make_mock_class('MockScrollbar', 'Scrollbar')):
    """Mock Scrollbar widget."""

    def __init__(self, master=None, **kwargs):
        _MockBase.__init__(self, master, **kwargs)
        self._master = master
        if master is not None and hasattr(master, '_mock_children'):
            master._mock_children.append(self)
        self._mock_attrs.update(kwargs)
        self._command = kwargs.get('command', None)
        self._mock_config = {}
        self._first = 0.0
        self._last = 1.0

    def config(self, **kwargs):
        return self.configure(**kwargs)

    def configure(self, **kwargs):
        if 'command' in kwargs:
            self._command = kwargs['command']

    def set(self, first, last):
        """Set the scrollbar range [first, last]."""
        self._first = first
        self._last = last

    def yview(self, *args):
        """Text widget scroll callback - no-op mock."""
        return None


# -----------------------------------------------------------------------
# Headless setup utilities
# -----------------------------------------------------------------------

def setup_headless():
    """Configure environment for headless tkinter testing.

    Sets TKINTER_DONT_WAIT_FOR_DISPLAY and optionally matplotlib to use
    a non-GUI backend.
    """
    os.environ.setdefault('TKINTER_DONT_WAIT_FOR_DISPLAY', '1')
    os.environ.setdefault('MATPLOTLIB_BACKEND', 'Agg')

    # Try to prevent tkinter from actually initializing
    try:
        import matplotlib
        matplotlib.use('Agg', force=True)
    except Exception:
        pass


def apply_mocks():
    """Apply mocks to the tkinter module in sys.modules.

    After calling this, any code that imports `from tkinter import Tk`
    or `import tkinter as tk` will get the mock classes instead.

    This should be called BEFORE importing agent.ui.
    """
    setup_headless()

    # Create mock tkinter module
    import types

    tkinter_mock = types.ModuleType('tkinter')
    tkinter_mock.Tk = MockTk
    tkinter_mock.Text = MockText
    tkinter_mock.Button = MockButton
    tkinter_mock.Label = MockLabel
    tkinter_mock.Frame = MockFrame
    tkinter_mock.PanedWindow = MockPanedWindow
    tkinter_mock.Scrollbar = MockScrollbar

    # Constants
    tkinter_mock.HORIZONTAL = 'horizontal'
    tkinter_mock.VERTICAL = 'vertical'
    tkinter_mock.WORD = 'word'
    tkinter_mock.CHAR = 'char'
    tkinter_mock.END = 'end'
    tkinter_mock.INSERT = 'insert'
    tkinter_mock.CURRENT = 'current'
    tkinter_mock.NORMAL = 'normal'
    tkinter_mock.DISABLED = 'disabled'
    tkinter_mock.ACTIVE = 'active'
    tkinter_mock.HIDDEN = 'hidden'
    tkinter_mock.RAISED = 'raised'
    tkinter_mock.SUNKEN = 'sunken'
    tkinter_mock.FLAT = 'flat'
    tkinter_mock.GROOVE = 'groove'
    tkinter_mock.RIDGE = 'ridge'
    tkinter_mock.S = 's'
    tkinter_mock.N = 'n'
    tkinter_mock.W = 'w'
    tkinter_mock.E = 'e'
    tkinter_mock.CENTER = 'center'
    tkinter_mock.BOTH = 'both'
    tkinter_mock.X = 'x'
    tkinter_mock.Y = 'y'
    tkinter_mock.LEFT = 'left'
    tkinter_mock.RIGHT = 'right'
    tkinter_mock.TOP = 'top'
    tkinter_mock.BOTTOM = 'bottom'
    tkinter_mock.NONE = 'none'
    tkinter_mock.WORD = 'word'
    tkinter_mock.CHAR = 'char'
    tkinter_mock.LINE = 'line'
    tkinter_mock.EXTENSIONS = 'extensions'
    tkinter_mock.TCL_VERSION = '8.6'
    tkinter_mock.TK_VERSION = '8.6'
    tkinter_mock.YES = 'yes'
    tkinter_mock.NO = 'no'

    # MessageBox constants
    tkinter_mock.OK = 'ok'
    tkinter_mock.CANCEL = 'cancel'
    tkinter_mock.YESNO = 'yesno'
    tkinter_mock.QUESTION = 'question'
    tkinter_mock.ERROR = 'error'
    tkinter_mock.INFO = 'info'
    tkinter_mock.WARNING = 'warning'

    # Also expose as module-level attributes directly
    _constants = {
        'YES': 'yes', 'NO': 'no', 'TOP': 'top', 'BOTTOM': 'bottom',
        'LEFT': 'left', 'RIGHT': 'right', 'BOTH': 'both', 'X': 'x', 'Y': 'y',
        'N': 'n', 'S': 's', 'E': 'e', 'W': 'w', 'CENTER': 'center',
        'NORMAL': 'normal', 'DISABLED': 'disabled', 'ACTIVE': 'active',
        'HIDDEN': 'hidden', 'RAISED': 'raised', 'SUNKEN': 'sunken',
        'FLAT': 'flat', 'GROOVE': 'groove', 'RIDGE': 'ridge',
        'HORIZONTAL': 'horizontal', 'VERTICAL': 'vertical',
        'END': 'end', 'INSERT': 'insert', 'WORD': 'word', 'CHAR': 'char',
    }
    for _name, _val in _constants.items():
        setattr(tkinter_mock, _name, _val)

    # Replace in sys.modules
    sys.modules['tkinter'] = tkinter_mock

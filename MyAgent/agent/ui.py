# -*- coding: utf-8 -*-
"""
MyAgent Tkinter UI - Task E1: UI-REPL Integration

Phase 3 core wiring between MyAgentWindow (ui.py) and REPL subprocess
(loop_v2.py):
- start() launches REPL subprocess + starts polling loop
- _on_start_task() writes task to io/input.txt
- _on_submit_response() writes LLM response to io/response.txt
- _poll_io_files() watches io/ directory for prompt.txt/final_answer.txt
- State machine: IDLE → GENERATING_PROMPT → WAITING_RESPONSE →
  PROCESSING → IDLE

Python 3.7.4 compatible (no f-strings, walrus, async).
"""
import os
import sys
import queue
import datetime
import tkinter as tk
import threading
import subprocess
import pathlib


class MyAgentWindow(object):
    """
    Main MyAgent UI window.

    Layout:
    - Top: PanedWindow (horizontal split)
      - Left panel: ~400px (control console)
      - Right panel: ~500px (LLM interaction)
    - Bottom: Status bar Frame + Label
    """

    # Color palette for simple clean light theme (Task E5)
    COLORS = {
        'bg_main': '#ffffff',        # Main window background (white)
        'bg_panel': '#f0f0f0',       # Panel background (light gray)
        'text_main': '#333333',      # Main text (dark gray) - 用户输入的实际内容用深色
        'text_dim': '#808080',       # Placeholder/dim text (medium gray)
        'btn_bg': '#f0f0f0',         # Button background (light gray)
        'btn_fg': '#333333',         # Button foreground (dark gray)
        'btn_active': '#e0e0e0',     # Button active/hover background
        'btn_border': '#cccccc',     # Button border color
        'status_bg': '#e8f4fd',      # Status bar background (light blue)
        'status_text': '#333333',    # Status bar text (dark gray)
        'input_bg': '#ffffff',       # Input text background (white)
        'border': '#cccccc',         # Border color
    }

    def __init__(self, root=None):
        """
        Create the MyAgent window.

        Args:
            root: tkinter Tk root. If None, creates a new Tk().
        """
        if root is None:
            self.root = tk.Tk()
        else:
            self.root = root

        # Task E1: REPL integration (io_dir set in start(), state machine)
        self._io_dir = None
        self._repl_process = None
        self._repl_state = 'IDLE'
        self._last_prompt = ''
        self._last_final = ''
        self._placeholder_text = '\u8bf7\u5728\u8fd9\u91cc\u8f93\u5165\u4efb\u52a1\uff0c\u8f93\u5165 quit \u9000\u51fa...'

        self._setup_root()
        self._create_paned_window()
        self._create_console_panel()
        self._create_status_bar()
        self._create_llm_panel()

        # Task B1: Real-time log Queue + after_poll
        self._log_queue = queue.Queue()
        self.root.after(100, self._poll_log_queue)

        # Task B2: Interrupt mechanism
        self._interrupt_event = threading.Event()

    def _setup_root(self):
        """Configure root window: title, size, and white background."""
        self.root.title("MyAgent v2")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)
        self.root.configure(bg=self.COLORS['bg_main'])

    def _create_paned_window(self):
        """Create the left/right PanedWindow split."""
        self._paned = tk.PanedWindow(
            self.root,
            orient=tk.HORIZONTAL,
            sashrelief=tk.RAISED,
            sashwidth=4,
            bg=self.COLORS['bg_main']
        )
        self._paned.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)

        # Left panel: ~400px wide (control console)
        self._left_panel = tk.Frame(
            self._paned, width=400, height=600,
            bg=self.COLORS['bg_panel']
        )
        self._left_panel.pack_propagate(False)  # keep explicit width
        self._paned.add(self._left_panel)

        # Right panel: ~500px wide (LLM interaction)
        self._right_panel = tk.Frame(
            self._paned, width=500, height=600,
            bg=self.COLORS['bg_panel']
        )
        self._right_panel.pack_propagate(False)  # keep explicit width
        self._paned.add(self._right_panel)

        # Let the panedwindow size itself, then set sash position
        self.root.update_idletasks()
        total_w = self._paned.winfo_width()
        if total_w < 1:
            total_w = 900
        # Place sash at 400px from left
        self._paned.sash_place(0, 400, 0)

        # After sash_place, update and verify
        self.root.update_idletasks()

    def _create_console_panel(self):
        """Create the left panel control console layout."""
        colors = self.COLORS

        # Task input section: Label + Text (~80px high)
        input_frame = tk.Frame(self._left_panel, bg=colors['bg_panel'])
        input_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(5, 2))
        tk.Label(
            input_frame,
            text="\u4efb\u52a1\u8f93\u5165",
            font=("Segoe UI", 10, "bold"),
            fg=colors['text_main'],
            bg=colors['bg_panel']
        ).pack(side=tk.TOP, anchor=tk.W)
        self._task_input_text = tk.Text(
            input_frame, height=3, wrap=tk.WORD,
            font=("Segoe UI", 10),
            bg=colors['input_bg'],
            fg=colors['text_dim'],
            insertbackground=colors['text_main'],
            selectbackground=colors['border']
        )
        self._task_input_text.pack(side=tk.TOP, fill=tk.X)
        # Placeholder hint text in dim color
        self._task_input_text.insert("1.0", self._placeholder_text)
        self._task_input_text.configure(fg=colors['text_dim'])
        self._task_input_text.bind("<FocusIn>", self._on_task_input_focus_in)
        self._task_input_text.bind("<FocusOut>", self._on_task_input_focus_out)
        self._task_input_text.bind("<Button-1>", self._on_task_input_click)

        # Start task button
        btn_frame = tk.Frame(self._left_panel, bg=colors['bg_panel'])
        btn_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(2, 5))
        self._start_task_btn = tk.Button(
            btn_frame,
            text="\u5f00\u59cb\u4efb\u52a1",
            font=("Segoe UI", 10, "bold"),
            bg=colors['btn_bg'],
            fg=colors['btn_fg'],
            activebackground=colors['btn_active'],
            relief=tk.FLAT,
            bd=1,
            padx=10, pady=5,
            command=self._on_start_task
        )
        self._start_task_btn.pack(side=tk.TOP, fill=tk.X)

        # Execution log section: Label + Text (scrollable, readonly, middle area)
        log_frame = tk.Frame(self._left_panel, bg=colors['bg_panel'])
        log_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES, padx=5, pady=(5, 2))
        tk.Label(
            log_frame,
            text="\u6267\u884c\u8fc7\u7a0b\u76d1\u63a7",
            font=("Segoe UI", 10, "bold"),
            fg=colors['text_main'],
            bg=colors['bg_panel']
        ).pack(side=tk.TOP, anchor=tk.W)
        # Scrollbar for log text
        log_scroll = tk.Scrollbar(log_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._exec_log_text = tk.Text(
            log_frame, height=15, state=tk.DISABLED,
            wrap=tk.WORD, font=("Cascadia Code", 9),
            yscrollcommand=log_scroll.set,
            bg=colors['input_bg'],
            fg=colors['text_main'],
            insertbackground=colors['text_main'],
            selectbackground=colors['border']
        )
        self._exec_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)
        log_scroll.config(command=self._exec_log_text.yview)

        # Interrupt button
        interrupt_frame = tk.Frame(self._left_panel, bg=colors['bg_panel'])
        interrupt_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(2, 5))
        self._interrupt_btn = tk.Button(
            interrupt_frame,
            text="\u6253\u65ad",
            font=("Segoe UI", 10),
            bg=colors['btn_bg'],
            fg=colors['btn_fg'],
            activebackground=colors['btn_active'],
            relief=tk.FLAT,
            bd=1,
            padx=10, pady=5,
            command=self._on_interrupt
        )
        self._interrupt_btn.pack(side=tk.TOP, fill=tk.X)

        # New task button
        new_task_frame = tk.Frame(self._left_panel, bg=colors['bg_panel'])
        new_task_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(2, 5))
        self._new_task_btn = tk.Button(
            new_task_frame,
            text="\u65b0\u4efb\u52a1",
            font=("Segoe UI", 10),
            bg=colors['btn_bg'],
            fg=colors['btn_fg'],
            activebackground=colors['btn_active'],
            relief=tk.FLAT,
            bd=1,
            padx=10, pady=5,
            command=self._on_new_task
        )
        self._new_task_btn.pack(side=tk.TOP, fill=tk.X)

    def _on_task_input_focus_in(self, event):
        """Remove placeholder text when user focuses on task input."""
        if self._task_input_text.get("1.0", tk.END).strip() == self._placeholder_text:
            self._task_input_text.delete("1.0", tk.END)
            self._task_input_text.configure(fg=self.COLORS['text_main'])

    def _on_task_input_focus_out(self, event):
        """Restore placeholder if task input is empty on focus out."""
        if not self._task_input_text.get("1.0", tk.END).strip():
            self._task_input_text.insert("1.0", self._placeholder_text)
            self._task_input_text.configure(fg=self.COLORS['text_dim'])

    def _on_task_input_click(self, event):
        """Handle click on task input - clear placeholder if present."""
        current = self._task_input_text.get("1.0", tk.END).strip()
        if current == self._placeholder_text:
            self._task_input_text.delete("1.0", tk.END)
            self._task_input_text.configure(fg=self.COLORS['text_main'])

    def _on_start_task(self):
        """Callback for '开始任务' button - writes task to io/input.txt."""
        user_input = self._task_input_text.get("1.0", tk.END).strip()
        if not user_input or user_input == self._placeholder_text:
            self.update_status("\u72b6\u6001: \u8bf7\u5148\u8f93\u5165\u4efb\u52a1")
            return
        if self._io_dir is None:
            # start() not called yet - set up io_dir minimally for tests
            project_root = pathlib.Path(os.path.dirname(os.path.dirname(__file__)))
            self._io_dir = project_root / 'io'
        # Write to io/input.txt
        input_file = pathlib.Path(self._io_dir) / 'input.txt'
        input_file.write_text(user_input, encoding='utf-8')
        # Clear task input widget
        self._task_input_text.delete("1.0", tk.END)
        self._task_input_text.insert("1.0", self._placeholder_text)
        self._task_input_text.configure(fg=self.COLORS['text_dim'])
        # Update state and log
        self._set_state('GENERATING_PROMPT')
        self.append_log("USER", "\u5f00\u59cb\u4efb\u52a1: " + user_input)
        self._notify_repl()

    def _on_interrupt(self):
        """Callback for '打断' button - sets interrupt event and resets UI state."""
        self._interrupt()

    def _on_new_task(self):
        """Callback for '新任务' button - clears task input, log, and resets state."""
        self._reset_interrupt()
        self._task_input_text.delete("1.0", tk.END)
        self._task_input_text.insert("1.0", self._placeholder_text)
        self._task_input_text.configure(fg=self.COLORS['text_dim'])
        self._exec_log_text.config(state=tk.NORMAL)
        self._exec_log_text.delete("1.0", tk.END)
        self._exec_log_text.config(state=tk.DISABLED)
        self._start_task_btn.config(state=tk.NORMAL)
        self.update_status("\u72b6\u6001: \u7b49\u5f85\u8f93\u5165")

    def _create_status_bar(self):
        """Create bottom status bar Frame with Label."""
        colors = self.COLORS
        self._status_bar = tk.Frame(
            self.root, height=30,
            relief=tk.SUNKEN, bd=1,
            bg=colors['status_bg']
        )
        self._status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self._status_label = tk.Label(
            self._status_bar,
            text="\u72b6\u6001: \u5c31\u7eea",
            anchor=tk.W,
            font=("Segoe UI", 9),
            fg=colors['status_text'],
            bg=colors['status_bg']
        )
        self._status_label.pack(fill=tk.X, padx=5, pady=2)

    def _create_llm_panel(self):
        """
        Create the right panel (LLM interaction zone).

        Layout (top to bottom):
        - Prompt frame: Label + Text(height=10, readonly) + Scrollbar + 复制prompt button
        - Response frame: Label + Text(height=10, editable) + Scrollbar + 粘贴&提交 button
        - 清空日志 button
        """
        colors = self.COLORS

        # --- Prompt section ---
        prompt_frame = tk.Frame(self._right_panel, bg=colors['bg_panel'])
        prompt_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES, padx=5, pady=(5, 0))

        prompt_label = tk.Label(
            prompt_frame,
            text="Prompt \u6587\u672c",
            anchor=tk.W,
            font=("Segoe UI", 9, "bold"),
            fg=colors['text_main'],
            bg=colors['bg_panel']
        )
        prompt_label.pack(side=tk.TOP, fill=tk.X)

        # Text widget with scrollbar (readonly)
        self._prompt_text = tk.Text(
            prompt_frame, height=10, wrap=tk.WORD, state=tk.DISABLED,
            bg=colors['input_bg'],
            fg=colors['text_main'],
            insertbackground=colors['text_main'],
            selectbackground=colors['border']
        )
        self._prompt_scrollbar = tk.Scrollbar(prompt_frame, command=self._prompt_text.yview)
        self._prompt_text.config(yscrollcommand=self._prompt_scrollbar.set)
        self._prompt_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._prompt_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)

        # 复制prompt button
        self._copy_prompt_btn = tk.Button(
            self._right_panel,
            text="\u590d\u5236 prompt",
            font=("Segoe UI", 9),
            bg=colors['btn_bg'],
            fg=colors['btn_fg'],
            activebackground=colors['btn_active'],
            relief=tk.FLAT,
            bd=1,
            padx=10, pady=5,
            command=self._on_copy_prompt
        )
        self._copy_prompt_btn.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(3, 0))

        # --- Response section ---
        response_frame = tk.Frame(self._right_panel, bg=colors['bg_panel'])
        response_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES, padx=5, pady=(5, 0))

        response_label = tk.Label(
            response_frame,
            text="Response \u7c98\u8d34\u533a",
            anchor=tk.W,
            font=("Segoe UI", 9, "bold"),
            fg=colors['text_main'],
            bg=colors['bg_panel']
        )
        response_label.pack(side=tk.TOP, fill=tk.X)

        # Text widget with scrollbar (editable)
        self._response_text = tk.Text(
            response_frame, height=10, wrap=tk.WORD,
            bg=colors['input_bg'],
            fg=colors['text_main'],
            insertbackground=colors['text_main'],
            selectbackground=colors['border']
        )
        self._response_scrollbar = tk.Scrollbar(response_frame, command=self._response_text.yview)
        self._response_text.config(yscrollcommand=self._response_scrollbar.set)
        self._response_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._response_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)

        # 粘贴&提交 button
        self._submit_response_btn = tk.Button(
            self._right_panel,
            text="\u7c98\u8d34 & \u63d0\u4ea4",
            font=("Segoe UI", 9),
            bg=colors['btn_bg'],
            fg=colors['btn_fg'],
            activebackground=colors['btn_active'],
            relief=tk.FLAT,
            bd=1,
            padx=10, pady=5,
            command=self._on_submit_response
        )
        self._submit_response_btn.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(3, 0))

        # 清空日志 button
        self._clear_llm_log_btn = tk.Button(
            self._right_panel,
            text="\u6e05\u7a7a\u65e5\u5fd7",
            font=("Segoe UI", 9),
            bg=colors['btn_bg'],
            fg=colors['btn_fg'],
            activebackground=colors['btn_active'],
            relief=tk.FLAT,
            bd=1,
            padx=10, pady=5,
            command=self._on_clear_llm_log
        )
        self._clear_llm_log_btn.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(3, 5))

    # -----------------------------------------------------------------------
    # Button callbacks
    # -----------------------------------------------------------------------

    def _on_copy_prompt(self):
        """Copy prompt text content to system clipboard."""
        content = self._prompt_text.get("1.0", tk.END).strip()
        self.root.clipboard_clear()
        if content:
            self.root.clipboard_append(content)

    def _on_submit_response(self):
        """Handle paste & submit button click - writes response to io/response.txt."""
        resp = self._response_text.get("1.0", tk.END).strip()
        if not resp:
            self.update_status("\u72b6\u6001: response \u533a\u57df\u4e3a\u7a7a")
            return
        if self._io_dir is None:
            project_root = pathlib.Path(os.path.dirname(os.path.dirname(__file__)))
            self._io_dir = project_root / 'io'
        response_file = pathlib.Path(self._io_dir) / 'response.txt'
        response_file.write_text(resp, encoding='utf-8')
        self._response_text.delete("1.0", tk.END)
        self._set_state('PROCESSING')
        self.append_log("USER", "\u5df2\u63d0\u4ea4 LLM \u56de\u590d")
        self._notify_repl()

    def _on_clear_llm_log(self):
        """Clear prompt and response text widgets."""
        self._prompt_text.config(state=tk.NORMAL)
        self._prompt_text.delete("1.0", tk.END)
        self._prompt_text.config(state=tk.DISABLED)
        self._response_text.delete("1.0", tk.END)

    def _update_button_states(self):
        """Update button enabled/disabled states based on REPL state.

        Button protection rules (Task E7):
        - [_start_task_btn] NORMAL only in IDLE with non-empty non-placeholder input,
          DISABLED otherwise
        - [_interrupt_btn] NORMAL in GENERATING_PROMPT/WAITING_RESPONSE/PROCESSING,
          DISABLED in IDLE
        - [_submit_response_btn] NORMAL only in WAITING_RESPONSE, DISABLED otherwise
        """
        state = self._repl_state
        is_idle = (state == 'IDLE')

        # Check if task input has actual content (not empty, not placeholder)
        input_content = self._task_input_text.get("1.0", tk.END).strip()
        has_input = bool(input_content) and input_content != self._placeholder_text

        # Start button: enabled only in IDLE with real input
        if is_idle and has_input:
            self._start_task_btn.config(state=tk.NORMAL)
        else:
            self._start_task_btn.config(state=tk.DISABLED)

        # Interrupt button: enabled in non-IDLE states
        if is_idle:
            self._interrupt_btn.config(state=tk.DISABLED)
        else:
            self._interrupt_btn.config(state=tk.NORMAL)

        # Submit response button: enabled only in WAITING_RESPONSE
        if state == 'WAITING_RESPONSE':
            self._submit_response_btn.config(state=tk.NORMAL)
        else:
            self._submit_response_btn.config(state=tk.DISABLED)

    # -----------------------------------------------------------------------
    # Task E1: State machine
    # -----------------------------------------------------------------------

    def _set_state(self, state):
        """Update REPL state and status bar label."""
        self._repl_state = state
        labels = {
            'IDLE': '\u72b6\u6001: \u5c31\u7eea',
            'GENERATING_PROMPT': '\u72b6\u6001: \u6b63\u5728\u751f\u6210 prompt...',
            'WAITING_RESPONSE': '\u72b6\u6001: \u7b49\u5f85 LLM \u56de\u590d',
            'PROCESSING': '\u72b6\u6001: \u5904\u7406\u4e2d...',
        }
        self._status_label.config(text=labels.get(state, state))

        # Add guidance to log
        if state == 'GENERATING_PROMPT':
            self.append_log('SYSTEM', '\u6b63\u5728\u751f\u6210 prompt\uff0c\u8bf7\u7a0d\u5019...')
        elif state == 'WAITING_RESPONSE':
            self.append_log('SYSTEM', '\u2705 prompt \u5df2\u751f\u6210\uff01\u8bf7\u590d\u5236\u5230 LLM\uff0c\u7c98\u8d34\u56de\u590d\u540e\u70b9\u51fb\u201c\u7c98\u8d34&\u63d0\u4ea4\u201d')
        elif state == 'PROCESSING':
            self.append_log('SYSTEM', '\u6b63\u5728\u5904\u7406 LLM \u56de\u590d...')
        elif state == 'IDLE' and self._last_final:
            self.append_log('SYSTEM', '\u2705 \u4efb\u52a1\u5b8c\u6210\uff01')

    # -----------------------------------------------------------------------
    # Task E1: REPL subprocess management
    # -----------------------------------------------------------------------

    def start(self):
        """Initialize io/ directory, start REPL subprocess, begin polling."""
        # Resolve io/ directory relative to project root
        project_root = pathlib.Path(os.path.dirname(os.path.dirname(__file__)))
        self._io_dir = project_root / 'io'
        self._io_dir.mkdir(exist_ok=True)
        self._last_prompt = ''
        self._last_final = ''
        self._repl_process = None
        self._repl_state = 'IDLE'

        self._start_repl_subprocess()
        self.root.after(500, self._poll_io_files)

    def _start_repl_subprocess(self):
        """Launch loop_v2.py as a subprocess with piped stdin/stdout."""
        env = dict(os.environ)
        env['PYTHONIOENCODING'] = 'utf-8'
        # 显式从 User 环境变量读取（os.environ 不包含 User 级变量）
        user_api_key = subprocess.run(
            ['powershell', '-Command', "[Environment]::GetEnvironmentVariable('MINIMAX_API_KEY', 'User')"],
            capture_output=True, text=True, encoding='utf-8'
        ).stdout.strip()
        env['MINIMAX_API_KEY'] = user_api_key
        loop_v2_path = pathlib.Path(__file__).parent.parent / 'agent' / 'loop_v2.py'
        self._repl_process = subprocess.Popen(
            [sys.executable, str(loop_v2_path)],
            cwd=str(pathlib.Path(__file__).parent.parent),
            env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True, bufsize=1, encoding='utf-8'
        )
        t = threading.Thread(target=self._read_repl_stdout, daemon=True)
        t.start()

    def _read_repl_stdout(self):
        """Read REPL stdout line-by-line in a daemon thread."""
        for line in self._repl_process.stdout:
            print('[REPL]', line.rstrip())

    def _notify_repl(self):
        """Write newline to REPL stdin to trigger file read."""
        if self._repl_process and self._repl_process.stdin:
            self._repl_process.stdin.write('\n')
            self._repl_process.stdin.flush()

    def _poll_io_files(self):
        """Poll io/ directory for prompt.txt and final_answer.txt changes."""
        # Check prompt.txt
        prompt_file = pathlib.Path(self._io_dir) / 'prompt.txt'
        if prompt_file.exists():
            content = prompt_file.read_text(encoding='utf-8').strip()
            if content and content != self._last_prompt:
                self._last_prompt = content
                self._prompt_text.config(state=tk.NORMAL)
                self._prompt_text.delete('1.0', tk.END)
                self._prompt_text.insert('1.0', content)
                self._prompt_text.config(state=tk.DISABLED)
                self._set_state('WAITING_RESPONSE')
                self.append_log("SYSTEM", "\u2699 prompt \u5df2\u751f\u6210\uff01\u8bf7\u590d\u5236\u5230 LLM\uff0c\u7c98\u8d34\u56de\u590d\u540e\u70b9\u51fb\u201c\u7c98\u8d34&\u63d0\u4ea4\u201d")
        # Check final_answer.txt
        final_file = pathlib.Path(self._io_dir) / 'final_answer.txt'
        if final_file.exists():
            content = final_file.read_text(encoding='utf-8').strip()
            if content and content != self._last_final:
                self._last_final = content
                self._write_final_answer(content)
                self._set_state('IDLE')
                self.append_log("SYSTEM", "\u2699 \u4efb\u52a1\u5b8c\u6210\uff01")
        self.root.after(500, self._poll_io_files)

    # -----------------------------------------------------------------------
    # Task B2: Interrupt mechanism
    # -----------------------------------------------------------------------

    def _interrupt(self):
        """Set the interrupt event (called from UI thread)."""
        self._interrupt_event.set()

    def _is_interrupted(self):
        """Return True if interrupt has been requested."""
        return self._interrupt_event.is_set()

    def _check_interrupt(self):
        """Check interrupt event and raise InterruptedError if set.

        Called by worker threads during tool execution to detect
        user-requested interruption.
        """
        if self._interrupt_event.is_set():
            raise InterruptedError("Task interrupted by user")

    def _reset_interrupt(self):
        """Clear the interrupt event (called from UI thread after handling)."""
        self._interrupt_event.clear()

    # -----------------------------------------------------------------------
    # Task B3: timestamped log formatting
    # -----------------------------------------------------------------------

    def _log_message(self, log_type, msg):
        """Format a log entry with timestamp and type prefix.

        Format: HH:MM:SS.mmm  [TYPE]  message

        Args:
            log_type: TYPE category string (USER/AGENT/TOOL/SYSTEM/ERROR)
            msg: message text

        Returns:
            Formatted string with timestamp and type prefix.
        """
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        return "{}  [{}]  {}".format(ts, log_type, msg)

    # -----------------------------------------------------------------------
    # Task B1: Real-time log Queue polling
    # -----------------------------------------------------------------------

    def _poll_log_queue(self):
        """Poll the log queue and insert entries into _exec_log_text.

        Drains all available entries from _log_queue, inserts each into
        the _exec_log_text widget (handling DISABLED state), scrolls to
        end, then reschedules itself via root.after(100, ...).
        """
        while True:
            try:
                entry = self._log_queue.get_nowait()
                self._insert_log_safe(entry + "\n")
            except queue.Empty:
                break
        self.root.after(100, self._poll_log_queue)

    def _insert_log_safe(self, text):
        """Insert text into _exec_log_text, handling DISABLED state safely."""
        log_text = self._exec_log_text
        # Handle DISABLED state: enable temporarily, insert, restore
        was_disabled = (log_text.cget('state') == tk.DISABLED)
        if was_disabled:
            log_text.configure(state=tk.NORMAL)
        log_text.insert(tk.END, text)
        log_text.see(tk.END)
        if was_disabled:
            log_text.configure(state=tk.DISABLED)

    def _write_final_answer(self, content):
        """Insert final answer with separator into _exec_log_text."""
        was_disabled = (self._exec_log_text.cget('state') == tk.DISABLED)
        if was_disabled:
            self._exec_log_text.configure(state=tk.NORMAL)
        # Insert separator
        self._exec_log_text.insert(tk.END, '\n=== \u6700\u7ec8\u56de\u7b54 ===\n')
        # Insert content
        self._exec_log_text.insert(tk.END, content + '\n')
        self._exec_log_text.see(tk.END)
        if was_disabled:
            self._exec_log_text.configure(state=tk.DISABLED)

    def append_log(self, tag_or_msg, msg=None):
        """Append a log message to the queue (thread-safe).

        Supports two call signatures for backward compatibility:
        - append_log(msg)          -> tag defaults to "TOOL"
        - append_log(tag, msg)      -> explicit tag + message

        Args:
            tag_or_msg: tag string (when msg is provided) or message text
            msg: optional message text when first arg is a tag
        """
        if msg is None:
            # Backward-compatible: single arg is the message, default tag
            formatted = self._log_message("TOOL", tag_or_msg)
        else:
            # New signature: (tag, msg)
            formatted = self._log_message(tag_or_msg, msg)
        self._log_queue.put(formatted)

    def update_status(self, text):
        """Update the status bar label text."""
        self._status_label.config(text=text)

    def mainloop(self):
        """Enter the tkinter main loop."""
        self.root.mainloop()


if __name__ == '__main__':
    win = MyAgentWindow()
    win.start()
    win.mainloop()
    if win._repl_process:
        win._repl_process.terminate()
        try:
            win._repl_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            win._repl_process.kill()
# MyAgent GUI-less 测试框架设计方案 (P1)

> 目标：消除 tkinter 对无头（headless）测试环境的依赖，使现有 UI 测试套件可在无显示器/CI 环境下稳定运行。

---

## 1. 挂起测试分析

共 8 个被标记为"挂起"的测试文件。以下按 **GUI 依赖程度** 分三类：

### A 类：完全 GUI 依赖（必须在可见窗口中运行）

| 文件 | 问题 | 推荐处置 |
|------|------|----------|
| `test_ui_full_loop.py` | 使用 `pyautogui` + `pyperclip` 做像素级 GUI 自动化，依赖窗口坐标、系统剪贴板、可见屏幕 | 移至 `tests/gui_manual/` 作为人工验收测试，**永不**在 CI 中运行 |
| `test_ui_repl_loop.py` | 同上，pyautogui + MiniMax API 调用，使用固定坐标点击 UI | 同上 |

### B 类：中等依赖——需要 Tk root 但可 mock

| 文件 | 挂起根因 | 建议 |
|------|----------|------|
| `test_ui_integration.py` | `setUpClass` 创建 `tk.Tk()`，每个测试 `MyAgentWindow(self.root)` 重新创建 UI；多个测试竞争同一 root 导致事件循环状态混乱 | 用 `mock_tkinter` fixture 替代真实 root |
| `test_ui_skeleton.py` | 同上，shared root 被重复创建销毁导致 Tcl 资源耗尽 | 同上 |
| `test_timestamp_log.py` | 调用 `_poll_log_queue()` → `root.after(100, callback)` 调度定时任务；无头环境下 after 回调执行异常 | mock `root.after` 支持手动触发（`root._run_after()`） |
| `test_realtime_log.py` | 同上 | 同上 |
| `test_merged_log_panel.py` | 同上 | 同上 |

### C 类：无真正 GUI 依赖（误分类）

| 文件 | 问题 | 推荐处置 |
|------|------|----------|
| `test_process_status.py` | 纯测 `ProcessStatusTool`，不含任何 tkinter 调用；挂起原因可能是测试隔离问题（import 顺序、共享进程状态） | 修复测试隔离，移入标准 pytest，无 GUI mock 需要 |

---

## 2. Mock 方案详细设计

### 2.1 总体策略

**不 mock `tkinter` 模块本身**（那样会污染全局状态），而是：

1. 在 `tests/` 下创建 `mock_tkinter.py`，定义一套**纯 Python 数据结构**的 mock widget 类
2. 在 `conftest.py` 中提供 `mock_root` fixture，注入 `MyAgentWindow.__init__` 替代真实 `tk.Tk()`
3. 对需要 `root.after()` 调度的测试，提供 `mock_root.step()` 方法手动驱动事件循环

### 2.2 MockTk（MockRoot）

```python
class MockRoot:
    """替代 tkinter.Tk() 的 mock root。"""
    def __init__(self):
        self._afterCallbacks = []   # [(delay, callback), ...]
        self._widgets = []           # 注册的子 widget
        self._window_title = "MyAgent v2"
        self._geometry = "1200x800"
        self._bg = "#ffffff"
        self._called = {}            # 调试/断言用：记录方法调用

    # ---- Tk 核心接口 ----
    def title(self, s=None):
        if s is None: return self._window_title
        self._window_title = s

    def geometry(self, s=None):
        if s is None: return self._geometry
        self._geometry = s

    def configure(self, **kw):
        self._bg = kw.get('bg', self._bg)

    def withdraw(self): pass
    def deiconify(self): pass
    def destroy(self): pass
    def update_idletasks(self): pass
    def update(self): pass

    # ---- after 调度 ----
    def after(self, delay, callback):
        """调度 delay ms 后执行 callback。返回 callback（可被 after_cancel）。"""
        self._afterCallbacks.append((delay, callback))
        return callback

    def after_cancel(self, handle):
        self._afterCallbacks = [(d, c) for d, c in self._afterCallbacks if c != handle]

    def _step(self, max_callbacks=None):
        """手动驱动所有已调度的 after 回调（测试用）。
        每次调用执行所有当前已注册的回调，可多次调用模拟时间流逝。"""
        cbs = self._afterCallbacks[:]
        self._afterCallbacks = []
        count = 0
        for delay, cb in cbs:
            cb()
            count += 1
            if max_callbacks and count >= max_callbacks:
                break
```

### 2.3 MockWidget（所有 widget 的基类）

```python
class MockWidget:
    _uid = 0
    def __init__(self, master=None, **kw):
        self._master = master
        self._children = []
        self._config = dict(kw)
        self._uid = MockWidget._uid
        MockWidget._uid += 1
        if master:
            master._children.append(self)

    def config(self, **kw):
        self._config.update(kw)
    configure = config

    def cget(self, key):
        return self._config.get(key)
```

### 2.4 MockFrame

```python
class MockFrame(MockWidget):
    def pack(self, **kw): self._pack_info = kw
    def pack_propagate(self, v): self._propagate = v
    def update_idletasks(self): pass
```

### 2.5 MockLabel

```python
class MockLabel(MockWidget):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self._text = self._config.get('text', '')
    def config(self, **kw):
        super().config(**kw)
        if 'text' in kw: self._text = kw['text']
    def cget(self, key):
        if key == 'text': return self._text
        return super().cget(key)
```

### 2.6 MockButton

```python
class MockButton(MockWidget):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self._text = self._config.get('text', '')
        self._command = self._config.get('command')
        self._state = self._config.get('state', 'normal')

    def config(self, **kw):
        super().config(**kw)
        if 'text' in kw: self._text = kw['text']
        if 'command' in kw: self._command = kw['command']
        if 'state' in kw: self._state = kw['state']
    cget = config  # button.cget('text') == button['text']

    def invoke(self):
        if self._command and self._state != 'disabled':
            self._command()
```

### 2.7 MockText（核心，行为最复杂）

```python
class MockText(MockWidget):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self._lines = [""]          # 所有行
        self._state = self._config.get('state', 'normal')

    # ---- 属性代理（使 widget['fg'] 等价于 widget.cget('fg')）----
    def __getitem__(self, key): return self.cget(key)
    def __setitem__(self, key, v): self.config(**{key: v})

    def config(self, **kw):
        super().config(**kw)
        for k in ('state', 'fg', 'bg', 'font', 'wrap', 'yscrollcommand',
                  'insertbackground', 'selectbackground'):
            if k in kw: self._config[k] = kw[k]
        if 'state' in kw: self._state = kw['state']

    def cget(self, key):
        if key == 'state': return self._state
        return self._config.get(key)

    # ---- 文本操作（tkinter Text 索引约定）----
    def get(self, start="1.0", end=None):
        if end is None:
            end = f"{len(self._lines)}.{len(self._lines[-1])}"
        # 简化：返回当前所有内容（忽略精确索引）
        return "\n".join(self._lines)

    def delete(self, start, end=None):
        if start == "1.0" and end is None:
            end = "end"
        if start == "1.0" and end == "end":
            self._lines = [""]
            return
        # 简化处理

    def insert(self, index, text):
        if index == tk.END or index == "end":
            self._lines[-1] += text
            return
        # 其他索引简化处理

    def configure(self, **kw):
        self.config(**kw)
    state = property(lambda self: self._state, lambda self, v: self.config(state=v))

    # ---- DISABLED 安全包装（模拟 _insert_log_safe 行为）----
    def _safe_insert(self, index, text):
        """在 DISABLED 状态下执行临时启用+恢复的 insert。"""
        was_disabled = (self._state == 'disabled')
        if was_disabled:
            self._state = 'normal'
        self.insert(index, text)
        if was_disabled:
            self._state = 'disabled'
```

### 2.8 MockScrollbar

```python
class MockScrollbar(MockWidget):
    def config(self, **kw):
        super().config(**kw)
        if 'command' in kw:
            self._command = kw['command']
    def set(self, *args): pass
```

### 2.9 MockPanedWindow

```python
class MockPanedWindow(MockWidget):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self._panes = []
        self._sashes = []   # [(x, y), ...]
    def add(self, child, **kw): self._panes.append(child)
    def sash_place(self, idx, x, y): self._sashes.append((x, y))
    def sash_coord(self, idx): return self._sashes[idx] if idx < len(self._sashes) else (0, 0)
```

### 2.10 Mock tk 常量

```python
# 在 mock_tkinter.py 顶部
class _tk:
    class Tk:
        def __init__(self): ...   # 返回 MockRoot
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    RAISED = "raised"
    SUNKEN = "sunken"
    FLAT = "flat"
    WORD = "word"
    END = "end"
    DISABLED = "disabled"
    NORMAL = "normal"
    LEFT = "left"
    TOP = "top"
    RIGHT = "right"
    BOTTOM = "bottom"
    BOTH = "both"
    YES = "yes"
    X = "x"
    Y = "y"

# 用法: mock_tkinter.PanedWindow = MockPanedWindow
#        mock_tkinter.Button = MockButton
#        ...
```

### 2.11 Mock 模块注入机制

在 `conftest.py` 中通过 **monkeypatch** 注入 mock 模块：

```python
import sys
from unittest.mock import MagicMock
import tests.mock_tkinter as mock_tkinter

@pytest.fixture
def mock_tkinter_env(monkeypatch):
    """将所有 tkinter 调用替换为 mock 实现。"""
    # mock tkinter module
    sys.modules['tkinter'] = mock_tkinter
    sys.modules['tkinter.ttk'] = MagicMock()
    yield
    # restore
    sys.modules['tkinter'] = __import__('tkinter')
```

> **注意**：由于 `MyAgentWindow.__init__` 在行 61 调用 `tk.Tk()`，注入必须在 import `agent.ui` **之前**完成。推荐用 `@pytest.fixture(autouse=True)` + `sys.modules` 预热，或在测试文件顶部就完成 patch。

---

## 3. 测试分层架构

```
tests/
├── conftest.py                  # 全局 fixtures：tk_root, mock_tkinter_env
├── mock_tkinter.py               # Mock widget 实现（核心库）
├── mock_tkinter_ops.py           # 辅助：spy 调用记录器
│
├── unit/                         # Layer 1：纯逻辑单元测试（无 GUI）
│   ├── test_log_message.py       # 迁移自 test_timestamp_log.py
│   ├── test_append_log.py        # 迁移自 test_timestamp_log.py
│   ├── test_interrupt_event.py   # 迁移自 test_ui_integration.py
│   ├── test_button_protection.py # 迁移自 test_ui_integration.py
│   └── test_process_status.py    # 已在 C 类，无 mock 需要
│
├── unit_ui/                      # Layer 2：UI 逻辑测试（mock tkinter）
│   ├── test_ui_skeleton.py       # 迁移自 test_ui_skeleton.py
│   ├── test_ui_integration.py    # 迁移自 test_ui_integration.py
│   ├── test_realtime_log.py       # 迁移自 test_realtime_log.py
│   ├── test_merged_log_panel.py  # 迁移自 test_merged_log_panel.py
│   └── test_timestamp_log.py      # 迁移自 test_timestamp_log.py
│
├── integration/                  # Layer 3：集成测试（真实 tkinter，可 headless）
│   ├── test_repl_integration.py  # REPL subprocess + mock root（无真实 UI）
│   └── test_io_file_flow.py      # io 文件读写流程
│
├── gui_manual/                   # Layer 4：人工 GUI 验收测试（必须可见窗口）
│   ├── test_ui_full_loop.py      # 从 test_ui_full_loop.py 移来
│   └── test_ui_repl_loop.py      # 从 test_ui_repl_loop.py 移来
│
└── (root) conftest.py            # 共享全局 fixtures
```

### 分层说明

| Layer | 运行环境 | Tk 依赖 | 适用场景 | 执行频率 |
|-------|----------|---------|----------|----------|
| **L1** unit | any | 0 | 纯算法/工具函数/业务逻辑 | 每次 CI |
| **L2** unit_ui | headless | mock | UI 状态机、事件回调、按钮保护逻辑 | 每次 CI |
| **L3** integration | headless | real（hidden）| REPL 集成、文件 IO、状态流 | 每次 CI |
| **L4** gui_manual | visible display | real | 端到端 GUI 截图/坐标验证 | 人工/发布前 |

### 迁移原则

1. **L1**: 所有不含 `MyAgentWindow` 实例化的测试直接归入
2. **L2**: 所有含 `MyAgentWindow` 但只测回调/状态/队列的测试，改为用 `mock_root` fixture
3. **L3**: 需要真实 tkinter 组件（`winfo_*` 等），但不需要显示的测试，用 `tk_root` fixture
4. **L4**: 含有 `pyautogui`、`坐标`、`截图` 的测试无条件移入

---

## 4. 实施步骤和验收标准

### Phase 1：基础设施（预计 1 天）

**步骤 1.1**：创建 `tests/mock_tkinter.py`
- 实现 `MockRoot`、`MockFrame`、`MockLabel`、`MockButton`、`MockText`、`MockScrollbar`、`MockPanedWindow`
- 实现 `root.after()` 调度 + `root._step()` 手动驱动
- 实现 `MockText._safe_insert()` 模拟 DISABLED 临时提升

**验收标准**：
```python
# 独立可运行的冒烟测试
from tests.mock_tkinter import MockRoot, MockButton, MockText
root = MockRoot()
btn = MockButton(root, text="Test", command=lambda: None)
btn.invoke()  # 不抛异常
root._step()   # 不抛异常
```

**步骤 1.2**：更新 `tests/conftest.py`
- 废弃现有 `tk_shared_root` fixture（或保留作 L3 使用）
- 新增 `mock_tkinter_env` autouse fixture，patch `sys.modules['tkinter']`
- 提供 `mock_root` fixture 返回 `MockRoot()` 实例
- 提供 `ui_window(mock_root)` fixture 返回已构造的 `MyAgentWindow`（mock 版本）

**验收标准**：
```python
# conftest.py 内部验证
def test_conftest_smoke(mock_root):
    assert hasattr(mock_root, 'after')
    assert hasattr(mock_root, '_step')
```

### Phase 2：L2 测试迁移（预计 1-2 天）

**步骤 2.1**：迁移 `test_timestamp_log.py` → `tests/unit/test_timestamp_log.py`
- `setUpClass` 的 `tk.Tk()` 替换为 fixture `mock_root`
- 所有 `root.update()` 调用替换为 `mock_root.step()`
- 验证：pytest 无 tkinter 进程挂起，所有断言通过

**步骤 2.2**：迁移 `test_realtime_log.py` → `tests/unit_ui/test_realtime_log.py`
- 同上
- 特别验证 `_poll_log_queue` 在 mock 下的行为

**步骤 2.3**：迁移 `test_merged_log_panel.py` → `tests/unit_ui/test_merged_log_panel.py`
- 同上

**步骤 2.4**：迁移 `test_ui_skeleton.py` 和 `test_ui_integration.py`
- 这两个文件的测试方法（如 `test_status_bar_text`）验证 `win._status_label.cget('text')`
- mock 实现必须支持 `cget()` 方法链式调用

**验收标准**：
```bash
cd MyAgent
pytest tests/unit/ tests/unit_ui/ -v --timeout=10 2>&1 | tail -20
# 全部 PASSED，无 TK/Tcl 错误，无进程挂起
```

### Phase 3：L4 测试归档（预计 0.5 天）

**步骤 3.1**：
```bash
mkdir tests/gui_manual
mv tests/test_ui_full_loop.py tests/gui_manual/
mv tests/test_ui_repl_loop.py tests/gui_manual/
```
在两个文件顶部添加注释说明其用途和运行环境要求。

**验收标准**：文件存在于正确目录，原 import 路径兼容（pytest 可跳过或标记 skip）。

### Phase 4：L3 集成测试增强（可选，持续）

**步骤 4.1**：增强 `test_repl_integration.py`
- 使用 `tk_root` fixture（现有 conftest 的 session-scoped hidden root）
- 测试 `start()` / `_poll_io_files()` 逻辑（io 文件存在性、状态机转换）
- 不启动真实 REPL subprocess（mock 掉 `subprocess.Popen`）

### Phase 5：CI 验证（完成后执行）

**验收标准**：
```bash
# 必须全部通过，且无挂起
pytest tests/unit/ tests/unit_ui/ tests/integration/ \
    -v --timeout=30 -x 2>&1

# 无 TK 相关错误
pytest tests/ --co -q 2>&1 | grep -i "tcl\|tk\|display"  # 应无输出
```

---

## 5. 关键设计决策

1. **不 patch `tkinter` 源码**：直接 patch `sys.modules`，避免修改 `agent/ui.py`
2. **Mock 保守实现**：只实现各 widget 当前测试实际用到的 API，不过度设计
3. **`root.after()` 的 mock 策略**：mock 记录回调 + 手动触发（`step()`），而非用真实线程
4. **MockText 的 DISABLED 行为**：通过 `_safe_insert()` 显式模拟 `MyAgentWindow._insert_log_safe()` 的临时启用逻辑
5. **L1/L2 严格分离**：L1 彻底无 GUI import，L2 仅通过 fixture 获取 mock root

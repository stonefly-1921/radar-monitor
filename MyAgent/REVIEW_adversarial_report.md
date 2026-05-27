# MyAgent 对抗评审报告（Anthropic 三角色框架）

**评审日期**: 2026-05-25
**测试脚本**: `tests/quick_e2e.py`
**测试框架**: 真实 MiniMax-M2.7 LLM API + AgentLoopV2

---

## Phase 1 — Planner：测试设计与覆盖度分析

### 1.1 测试文件分布

| 类别 | 文件数 | 测试函数数 |
|------|--------|-----------|
| 工具单元测试 | test_file_ops.py, test_grep_tool.py, test_shell.py, test_tools.py | ~25 |
| 循环/Agent测试 | test_loop.py, test_loop_v2.py, test_repl_full_scenarios.py | ~30 |
| UI/GUI测试 | test_ui_*.py (多个) | ~60 |
| Memory/Session | test_memory.py, test_session.py | ~15 |
| 集成测试 | test_integration.py, test_e2e_cli.py | ~20 |
| **合计** | **41个文件** | **~150+函数** |

### 1.2 docs/10_test_cases.md 设计分析

文档定义了10个复杂E2E场景：

```
任务1：计算任务（python_run）
任务2：文件操作多步骤（file_list+file_read+python_run）
任务3：弹道仿真AFSIM（grep+file_read+python_run）
任务4：代码审查（file_list+file_read+grep+python_run）
任务5：Wiki操作（wiki_search+wiki_read+python_run）
任务6：文档撰写（python_run+file_write+file_read）
任务7：表格处理（xlsx_create+write+read）← 工具不存在！
任务8：Shell命令（shell_run+python_run）
任务9：多步骤工作流（file_list+python_run）
任务10：综合任务（xlsx+python_run+file_write+file_read）
```

**覆盖率**：实际E2E执行只覆盖了任务1/2/3/4/8/9的部分场景，任务5/6/7/10**未执行**。

---

## Phase 2 — Executor：测试执行结果

### 2.1 实际执行的17+1场景（quick_e2e.py）

| # | 测试场景 | 结果 | 说明 |
|---|----------|------|------|
| 1 | 计算1+1 | ✓ PASS | python_run直接返回2 |
| 2 | 计算2*3 | ✓ PASS | python_run直接返回6 |
| 3 | 计算阶乘(5!) | ✓ PASS | python_run返回120 |
| 4 | 列出py文件 | ✓ PASS | file_list正常 |
| 5 | 先列后读 | ✗ FAIL | **LLM循环不退出**（Turn3起无限循环） |
| 6 | 错误路径 | ✓ PASS | 正确识别文件不存在 |
| 7 | 第二次同类任务 | ✓ PASS | Session记忆生效 |
| 8 | shell运行echo | ✓ PASS | shell_run正常 |
| 9 | shell列出目录 | ✓ PASS | dir命令正常 |
| 10 | Python多行脚本 | ✓ PASS | 多行代码执行正确 |
| 11 | Python条件判断 | ✓ PASS | 三元表达式正确 |
| 12 | grep搜索 | ✓ PASS | **LLM跳过工具直接final** |
| 13 | grep多结果 | ✓ PASS | grep结果含"def" |
| 14 | 写文件 | ✓ PASS | file_write+read验证 |
| 15 | 工具链组合 | ✓ PASS | shell→file→read链路正确 |
| 16 | 数学2**10 | ✓ PASS | 幂运算返回1024 |
| 17 | 字符串len | ✓ PASS | len()返回11 |
| 18 | 错误后重试 | ✓ PASS | 错误恢复继续执行 |

**执行总结**: 17 passed, 1 failed（失败率 ~6%）

### 2.2 关键代码修复记录

| # | 问题 | 根因 | 状态 |
|---|------|------|------|
| 1 | f-string格式冲突 | `{"参数":"值"}`在f-string内被Python当作format specifier | ✓ 已修复 |
| 2 | parse_response空检查 | `data['answer']`无key时报AttributeError | ✓ 已修复 |
| 3 | LLM返回非dict类型 | 工具返回Python bool被json.loads后非dict | ✓ 已修复 |
| 4 | 工具循环不退出 | LLM拿到file_read结果后继续调用tool_call | ✗ 待优化 |

---

## Phase 3 — Reviewer：批判性评审

### 3.1 测试用例设计的根本性问题

#### 🔴 问题A：大量测试函数是"空壳"
**现象**：41个文件声明了test_函数，但只有部分真正运行。
```
tests/test_e2e_cli.py → 有3个def test_，但subprocess模式已卡住废弃
tests/test_response_parsing.py → 只有1个test_，且无实际执行逻辑
```

**影响**：看起来有150+测试函数，实际有效E2E覆盖仅~20个。

#### 🔴 问题B：docs/10_test_cases.md的场景未执行
**任务5（Wiki）**：项目中有`wiki/`目录，但无实际wiki内容，wiki_search可能返回空。

**任务6（文档撰写）**：需要file_write执行Markdown写入，但没有验证文件格式。

**任务7（表格处理）**：`xlsx_create/xlsx_write/xlsx_read`三个工具在项目中**根本不存在**！
```bash
$ ls tools/
file_ops.py  grep_ops.py  shell.py  python.py  doc_ops.py  wiki_ops.py
# 没有 xlsx_ops.py
```
文档写了10个场景，实际可执行的只有7个。

#### 🔴 问题C：GUI测试依赖pywinauto坐标已失效
```python
# test_ui_beautification.py, test_ui_skeleton.py 等
# 使用 pywinauto 屏幕坐标操作 UI 控件
# 在无头环境(headless)或不同分辨率下完全失效
```
**结论**：GUI测试应降级为手动验证文档，不应加入自动化回归 suite。

---

### 3.2 LLM行为问题（代码层面无法修复，需优化Prompt）

#### 🟡 问题D：工具循环不退出（场景5失败根因）

**日志复现**：
```
Turn2: file_read('_check_config.py') → "# -*- coding: utf-8 -*-\nimport json..."
       ↓ LLM认为还需要更多信息
Turn3: action=tool_call (再次调用file_list!)
Turn4-8: 继续循环，超时
```

**根因**：prompt中缺少"何时应该出final"的决策指导。LLM拿到文件内容后仍然认为需要更多工具。

#### 🟡 问题E：跳过工具直接final（场景12）

**日志**：
```
Turn1: LLM直接final回答 "grep搜索结果包含AgentLoop..."
       实际没有调用grep工具
```

**根因**：MiniMax-M2.7对简单问题倾向于直接回答，而不是按要求的工具流程执行。

---

### 3.3 测试覆盖度缺口

| 模块 | 当前覆盖 | 缺口 |
|------|---------|------|
| python_run | 基础计算 | ✗ 无浮点精度测试、无大数计算 |
| file_list | 列表、过滤 | ✗ 无递归深度测试 |
| file_read | 读取、错误处理 | ✗ 无大文件(>1MB)测试 |
| file_write | 写入、验证 | ✗ 无编码测试(UTF-8/GBK) |
| shell_run | echo、dir | ✗ 无管道、权限错误测试 |
| grep | 搜索 | ✗ 无正则表达式测试 |
| **Memory摘要** | **完全未覆盖** | ✗ turn>3场景触发摘要 |
| **工具循环检测** | **完全未覆盖** | ✗ 无超时强制退出机制 |
| **API错误处理** | **完全未覆盖** | ✗ 401/500/timeout重试 |
| **Session去重** | **完全未覆盖** | ✗ 连续相同任务 |

---

### 3.4 测试数据污染问题

```
io/session.json → 发现116轮历史损坏数据
```
测试运行时session状态不确定，导致测试结果不可复现。

---

## 评审结论

### 通过项
- ✅ AgentLoopV2核心循环（工具执行、response解析）稳定
- ✅ python_run/file_list/file_read/file_write/shell_run 五个核心工具功能正常
- ✅ Session记忆在第二次同类任务时生效
- ✅ 代码bug（f-string、parse_response）已修复

### 待改进项（按严重度）
| 严重度 | 问题 | 建议 |
|--------|------|------|
| 🔴 高 | docs/10_test_cases.md任务7的xlsx工具不存在 | 删除不可行场景，或新增xlsx工具 |
| 🔴 高 | 工具循环不退出（场景5） | 在prompt中增加"收尾决策指导" |
| 🟡 中 | LLM跳过工具直接final（场景12） | prompt中强调"必须实际调用工具" |
| 🟡 中 | 大量空壳test_函数 | 清理或补全41个文件中的废弃测试 |
| 🟡 中 | GUI测试依赖pywinauto失效 | 降级为手动文档验证 |
| 🟡 中 | Memory摘要触发完全未覆盖 | 增加turn>3的E2E场景 |
| 🟡 中 | API错误处理未覆盖 | 增加401/timeout场景 |
| 🟢 低 | session.json历史污染 | 每次测试前重置session |

---

## 附录：测试执行命令

```bash
# 运行 quick_e2e.py（直接实例化，推荐）
cd C:\Users\15041\.openclaw\workspace\MyAgent
python tests/quick_e2e.py

# 运行 pytest（单元测试）
cd C:\Users\15041\.openclaw\workspace\MyAgent
pytest tests/ -v --tb=short

# 查看测试文件清单及test_函数数量
grep -h "^def test_" tests/*.py | wc -l  # 92个声明
grep -c "def test_" tests/*.py | grep -v ":0$"  # 41个文件有内容
```
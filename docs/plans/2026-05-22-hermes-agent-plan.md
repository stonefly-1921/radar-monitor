# Hermes-like Agent — 实现计划

> 日期：2026-05-22
> 状态：待实现

---

## 任务列表

每个任务遵循 TDD：写测试 → 写实现 → 验证

### Task 1: 项目目录结构

**目标**：创建完整的项目目录和基础文件

**步骤**：
1. 创建 `hermes-agent/` 目录结构
2. 创建所有 `__init__.py` 文件
3. 创建 `config/agent_config.json`
4. 创建 `config/tools_config.json`
5. 创建 `io/` 目录和示例文件
6. 创建 `requirements.txt`
7. 创建 `run.bat` 启动脚本
8. 创建 `README.md`

**验证**：
- `python -c "import agent; import memory; import tools"` 无报错

---

### Task 2: Persona 模块

**目标**：实现 Agent 人格配置

**步骤**：
1. 创建 `agent/persona.py`
   - 定义 `Persona` 类
   - 加载 persona 配置（名称、角色、行为准则、语气）
2. 创建 `agent/config.py`
   - 加载 `agent_config.json`
   - 提供配置访问接口
3. 创建 `agent/__init__.py`
4. 编写测试 `tests/test_persona.py`

**验证**：
- `python -c "from agent.persona import Persona; p = Persona(); print(p.name)"` 输出 "Hermes"

---

### Task 3: Memory 模块

**目标**：实现三层记忆架构

**步骤**：
1. 创建 `memory/storage.py`
   - 实现 JSON 文件读写
   - `save()` 和 `load()` 方法
2. 创建 `memory/context.py`
   - 实现上下文窗口管理
   - `truncate()` 截断过长上下文
3. 创建 `memory/core.py`
   - 实现 `Memory` 类
   - `add_turn()`, `get_conversation()`, `search()`, `summarize()`
   - 自动摘要机制（超过阈值时）
4. 创建 `memory/__init__.py`
5. 编写测试 `tests/test_memory.py`

**验证**：
- 添加 15 轮对话后，自动生成摘要

---

### Task 4: Tools 基类和工具注册

**目标**：实现工具基类和注册机制

**步骤**：
1. 创建 `tools/base.py`
   - 定义 `Tool` 基类
   - `name`, `description`, `parameters` 属性
   - `execute()` 和 `validate()` 方法
2. 创建 `tools/registry.py`
   - 实现工具注册表
   - `register_tool()`, `get_tool()`, `list_tools()`
3. 创建 `tools/__init__.py`
4. 编写测试 `tests/test_tools.py`

**验证**：
- `python -c "from tools.registry import ToolRegistry; r = ToolRegistry(); print(r.list_tools())"` 输出工具列表

---

### Task 5: 文件操作工具

**目标**：实现文件操作工具集

**步骤**：
1. 创建 `tools/file_ops.py`
   - `FileReadTool`: 读取文件
   - `FileWriteTool`: 写入文件
   - `FileEditTool`: 编辑文件
   - `FileListTool`: 列出目录
2. 在 `tools/__init__.py` 中注册工具
3. 编写测试 `tests/test_file_ops.py`

**验证**：
- 创建测试文件 → 用工具读取 → 内容一致

---

### Task 6: Shell 和 Python 执行工具

**目标**：实现命令执行工具

**步骤**：
1. 创建 `tools/shell.py`
   - `ShellRunTool`: 运行 shell 命令
2. 创建 `tools/python_exec.py`
   - `PythonRunTool`: 执行 Python 脚本
3. 在 `tools/__init__.py` 中注册
4. 编写测试 `tests/test_shell.py`

**验证**：
- `shell_run(command="echo hello")` 返回 "hello"
- `python_run(script="print(1+1)")` 返回 "2"

---

### Task 7: 文档知识库工具

**目标**：实现文档和知识库工具

**步骤**：
1. 创建 `tools/doc_wiki.py`
   - `DocReadTool`: 读取文档
   - `DocWriteTool`: 写文档
   - `WikiSearchTool`: 搜索知识库
   - `WikiUpdateTool`: 更新知识库
2. 在 `tools/__init__.py` 中注册
3. 编写测试 `tests/test_doc_wiki.py`

**验证**：
- 创建 wiki 条目 → 搜索 → 找到结果

---

### Task 8: Session 管理

**目标**：实现会话持久化管理

**步骤**：
1. 创建 `session.py`（根目录）
   - `Session` 类
   - `load_or_create()`: 加载或创建 session
   - `add_turn()`: 添加一轮对话
   - `save()`: 保存到文件
   - `load()`: 从文件加载
2. 创建 `io/session.json` 示例
3. 编写测试 `tests/test_session.py`

**验证**：
- 创建 session → 添加 turn → 保存 → 重新加载 → 数据一致

---

### Task 9: Agent Loop（核心）

**目标**：实现核心 Agent 循环

**步骤**：
1. 创建 `agent/loop.py`
   - `AgentLoop` 类
   - `load_or_create_session()`: 加载或创建 session
   - `load_input()`: 读取 input.json
   - `build_prompt()`: 构建提示词（含 Memory + 历史）
   - `save_prompt()`: 保存 prompt.json
   - `load_response()`: 读取 response.json
   - `parse_response()`: 解析响应类型
   - `execute_tool()`: 执行工具
   - `execute_turn()`: 执行单个 turn
   - `run()`: 主循环
2. 创建 `agent/__init__.py`
3. 编写测试 `tests/test_loop.py`（模拟文件输入输出）

**验证**：
- 创建 input.json → 运行 loop → 生成 prompt.json → 符合预期格式

---

### Task 10: 集成测试和 run.bat

**目标**：完整流程测试

**步骤**：
1. 创建完整的测试场景
   - 准备 input.json
   - 准备模拟的 response.json
   - 运行 loop
   - 验证 session.json 生成
2. 完善 `run.bat` 启动脚本
3. 更新 `README.md` 使用说明

**验证**：
- 双击 run.bat → 输入任务 → 完整交互流程 → 任务完成

---

## 执行顺序

```
Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6 → Task 7 → Task 8 → Task 9 → Task 10
```

每个 Task：
1. 创建目录/文件结构
2. 编写测试
3. 实现功能
4. 验证测试通过
5. 提交 commit

---

## 项目路径

所有文件创建在：
```
C:\Users\15041\.openclaw\workspace\hermes-agent\
```
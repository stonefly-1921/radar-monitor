# Hermes-like Agent Loop — 设计文档

> 日期：2026-05-22
> 状态：**草稿，待确认**

---

## 1. 项目概述

### 1.1 目标
在 Win7 内网环境下，构建一个**手动驱动大模型**的 Agent 框架。核心是一个 Python Agent Loop，通过文件交互方式与网页版大模型 API（Open WebUI）协作，实现智能体任务执行。

### 1.2 核心交互流程

```
用户写输入 → agent_loop.py 解析 → 生成提示词 JSON → 用户复制到网页版大模型
    ↑                                                                    ↓
    └──────────────── 响应 JSON ← 用户从大模型复制响应 ←───────────────┘
         ↑                                                                            ↓
         └────────────── 如需工具调用 → 执行工具 → 结果写入响应文件 ←────── 执行结果
```

### 1.3 技术约束
- **OS**: Windows 7
- **Python**: 3.7.4 (Conda 环境)
- **网络**: 内网隔离，不联网
- **大模型**: 通过 Open WebUI 网页版访问（需手动复制提示词/响应）
- **无网络工具**: 不包含 Web Search 等依赖互联网的工具

---

## 2. 项目结构（参照 Hermes）

```
hermes-agent/
├── agent/
│   ├── __init__.py
│   ├── persona.py          # Agent 人格设定
│   ├── config.py           # Agent 配置
│   └── loop.py             # 核心 Agent Loop
├── memory/
│   ├── __init__.py
│   ├── core.py             # 记忆核心管理
│   ├── storage.py          # 记忆存储
│   └── context.py         # 上下文管理
├── tools/
│   ├── __init__.py
│   ├── base.py             # 工具基类
│   ├── file_ops.py         # 文件操作工具
│   ├── shell.py            # Shell 命令工具
│   ├── python_exec.py      # Python 执行工具
│   └── doc_wiki.py        # 文档知识库工具
├── skills/
│   └── README.md           # Skills 说明文档
├── config/
│   ├── agent_config.json   # Agent 配置文件
│   └── tools_config.json  # 工具配置文件
├── io/
│   ├── session.json        # 会话持久化文件
│   ├── input.json          # 用户输入文件（用户编辑）
│   ├── prompt.json         # 生成的提示词文件（程序生成）
│   └── response.json       # 大模型响应文件（用户粘贴）
├── run.bat                 # Windows 启动脚本
├── requirements.txt        # Python 依赖
└── README.md              # 项目说明
```

---

## 3. 核心模块设计

### 3.1 Agent Loop（`agent/loop.py`）

**职责**：
1. 检查是否存在 `session.json`（继续上次会话）或 `input.json`（新会话）
2. 读取输入，结合 Memory 构建提示词
3. 生成 `io/prompt.json`（供用户复制到网页）
4. 等待用户粘贴大模型响应到 `io/response.json`
5. 解析响应：
   - 如果是**工具调用**：执行工具，结果追加到 response.json，继续循环
   - 如果是**最终回答**：保存到 session.json，输出结果
6. 支持多轮对话直到任务完成

**循环状态**：
```
IDLE → READ_INPUT → BUILD_PROMPT → WAIT_RESPONSE → PARSE_RESPONSE
    ↓                                    ↓
    ← ← ← ← （工具调用循环）← ← ← ← ←
    ↓
FINAL_ANSWER → SAVE_SESSION
```

**关键函数**：
- `load_or_create_session()` — 加载旧 session 或创建新 session
- `load_input()` — 读取 input.json
- `build_prompt()` — 构建提示词（含 Memory + 历史对话）
- `save_prompt()` — 保存 prompt.json
- `load_response()` — 读取 response.json
- `parse_response()` — 解析响应类型（回答/工具调用）
- `execute_tool()` — 执行工具
- `execute_turn()` — 执行单个 turn
- `save_session()` — 保存 session.json
- `run()` — 主循环

### 3.2 Memory（`memory/`）

**职责**：管理 Agent 的记忆和上下文

**组件**：
- `core.py`: 记忆管理器，支持添加、检索、总结记忆
- `storage.py`: 记忆持久化（JSON 文件存储）
- `context.py`: 上下文窗口管理（控制发送给大模型的上下文量）

**记忆结构**：
```json
{
  "short_term": [
    {"role": "user", "content": "...", "timestamp": "..."},
    {"role": "assistant", "content": "...", "timestamp": "..."}
  ],
  "long_term": [
    {"content": "...", "tags": ["..."], "timestamp": "..."}
  ],
  "summaries": [
    {"summary": "...", "timestamp": "..."}
  ]
}
```

**多轮对话支持**：
- Memory 会从 `session.json` 加载历史 turns
- 每次新 turn 构建 prompt 时，自动包含历史对话
- 支持自动摘要（当对话轮次超过阈值时）

### 3.3 Session 管理（`io/session.json`）

**设计原则**：
- 每个完整任务（从输入到最终回答）是一个 Turn
- 每个 session 包含多个 turns
- session 持久化到文件，下次运行时自动加载

**Session 结构**：
```json
{
  "session_id": "session_20260522_015400",
  "created_at": "2026-05-22T01:54:00+08:00",
  "updated_at": "2026-05-22T02:10:00+08:00",
  "status": "in_progress",
  "turns": [
    {
      "turn": 1,
      "input": "帮我读取 README.md",
      "prompt": "...",
      "response": "...",
      "tool_calls": [],
      "tool_results": [],
      "final_answer": "文件内容是..."
    }
  ],
  "memory": {
    "short_term": [...],
    "long_term": [...],
    "summaries": [...]
  }
}
```

### 3.4 Tools（`tools/`）

**基类设计**：
```python
class Tool:
    name: str          # 工具名称
    description: str  # 工具描述
    parameters: list  # 参数定义

    def execute(self, **kwargs) -> dict:
        """执行工具，返回结果"""
        pass

    def validate(self, params: dict) -> bool:
        """验证参数"""
        pass
```

**工具列表**：

| 工具名称 | 功能 | 参数 |
|---------|------|------|
| `file_read` | 读取文件 | `path` |
| `file_write` | 写入文件 | `path`, `content` |
| `file_edit` | 编辑文件 | `path`, `old_text`, `new_text` |
| `file_list` | 列出目录 | `path`, `pattern` |
| `shell_run` | 运行命令 | `command`, `cwd` |
| `python_run` | 执行脚本 | `script`, `timeout` |
| `doc_read` | 读文档 | `path` |
| `doc_write` | 写文档 | `path`, `content` |
| `wiki_search` | 搜索知识库 | `query` |
| `wiki_update` | 更新知识库 | `content` |

### 3.5 Persona（`agent/persona.py`）

**职责**：定义 Agent 的人格、行为准则、语气

**包含内容**：
- Agent 名称和角色
- 行为准则（如"先思考再行动"）
- 语气和说话风格
- 工具使用策略
- 自我约束规则

**示例结构**：
```json
{
  "name": "Hermes",
  "role": "智能助手",
  "guidelines": [
    "在执行前先理解任务目标",
    "使用最少的工具完成目标",
    "复杂任务分步骤执行"
  ],
  "style": {
    "language": "简洁专业",
    "emoji": false
  }
}
```

---

## 4. 文件交互协议

### 4.1 文件格式定义

**`io/input.json`** — 用户输入
```json
{
  "type": "input",
  "content": "用户的问题或指令",
  "timestamp": "2026-05-22T01:51:00+08:00"
}
```

**`io/prompt.json`** — Agent 生成的提示词
```json
{
  "type": "prompt",
  "system": "系统提示词（来自 persona）",
  "context": "Memory 中的相关上下文",
  "conversation": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "tools_available": ["file_read", "shell_run", ...],
  "timestamp": "2026-05-22T01:51:00+08:00"
}
```

**`io/response.json`** — 大模型响应（用户粘贴）
```json
{
  "type": "response",
  "content": "大模型的文本响应",
  "tool_calls": [
    {
      "tool": "file_read",
      "params": {"path": "test.txt"}
    }
  ],
  "timestamp": "2026-05-22T01:52:00+08:00"
}
```

**`io/tool_result.json`** — 工具执行结果（程序生成）
```json
{
  "type": "tool_result",
  "tool": "file_read",
  "result": "文件内容...",
  "success": true,
  "timestamp": "2026-05-22T01:53:00+08:00"
}
```

### 4.2 交互流程详解

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: 用户编辑 io/input.json                              │
│         → 写入想让 Agent 执行的任务                          │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: 用户运行 python agent\loop.py                       │
│         → 检查 session.json 是否存在（继续旧会话 or 新会话） │
│         → Agent Loop 读取 input.json                        │
│         → 结合 Memory + 历史对话 构建 prompt.json            │
│         → 显示 "[PROMPT_READY] 提示词已生成到 prompt.json"   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: 用户复制 prompt.json 内容 → 粘贴到 Open WebUI       │
│         → 网页大模型生成响应                                │
│         → 用户复制响应 → 粘贴到 response.json               │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Agent Loop 读取 response.json                      │
│         → 如果是工具调用：执行 → 生成 tool_result.json      │
│         → 用户将工具结果追加到 response.json，继续 Step 3    │
│         → 如果是最终回答：保存到 session.json → Loop 结束    │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. 配置管理

### 5.1 `config/agent_config.json`
```json
{
  "name": "Hermes",
  "version": "1.0.0",
  "persona_file": "agent/persona.py",
  "memory": {
    "short_term_max": 20,
    "long_term_enabled": true,
    "summary_threshold": 10
  },
  "session": {
    "auto_save": true,
    "max_turns_per_session": 50
  },
  "loop": {
    "max_iterations": 50,
    "tool_timeout": 30,
    "response_format": "json"
  },
  "io": {
    "session_file": "io/session.json",
    "input_file": "io/input.json",
    "prompt_file": "io/prompt.json",
    "response_file": "io/response.json",
    "tool_result_file": "io/tool_result.json"
  }
}
```

### 5.2 `config/tools_config.json`
```json
{
  "enabled_tools": [
    "file_read",
    "file_write",
    "file_edit",
    "file_list",
    "shell_run",
    "python_run",
    "doc_read",
    "doc_write",
    "wiki_search",
    "wiki_update"
  ],
  "tool_configs": {
    "shell_run": {
      "allowed_commands": ["dir", "type", "python", "pip"],
      "timeout": 60
    },
    "python_run": {
      "timeout": 120
    }
  }
}
```

---

## 6. 错误处理

### 6.1 文件不存在
- `input.json` 不存在 → 提示用户创建
- `response.json` 不存在 → 等待用户粘贴

### 6.2 工具执行失败
- 工具执行异常 → 返回错误信息到 `tool_result.json`
- 错误包含：`error`, `tool`, `params`, `message`

### 6.3 循环保护
- `max_iterations` 防止无限循环
- 每次迭代提示用户确认是否继续

---

## 7. 依赖安装

`requirements.txt`：
```
pathlib2==2.3.7  # Python 3.7 兼容
chardet==4.0.0   # 文件编码检测
```

> 注：主要使用 Python 3.7 内置库，额外依赖很少。

---

## 8. 使用示例

### 8.1 启动
```bash
cd hermes-agent
python agent\loop.py
# 或双击 run.bat
```

### 8.2 完整交互示例

**第一轮**：
```
用户编辑 io/input.json:
{"content": "帮我读取当前目录下的 README.md 文件内容"}

运行 python agent\loop.py:

> [1] 检测到新会话，创建 session.json
> [2] 读取输入... 完成
> [3] 构建提示词（含 persona + 空历史）... 完成
> [4] 提示词已生成到 io/prompt.json
> [5] 请将提示词复制到网页版大模型，等待响应...

用户复制 prompt.json → 粘贴到 Open WebUI → 获取响应 → 粘贴到 response.json

> [6] 解析响应... 检测到工具调用: file_read
> [7] 执行工具: file_read(path="README.md")
> [8] 工具执行成功，结果已写入 io/tool_result.json
> [9] 请将工具结果添加到 response.json，继续...

用户将工具结果写入 response.json，继续...

> [10] 解析响应... 最终回答
> [11] 任务完成！已保存到 session.json
```

**第二轮（继续会话）**：
```
用户编辑 io/input.json:
{"content": "继续分析这个文件"}

运行 python agent\loop.py:

> [1] 检测到已有 session.json，继续上次会话
> [2] 读取历史 turns，构建上下文
> [3] 读取输入... 完成
> [4] 构建提示词（含 persona + 第1轮对话）... 完成
> [5] 提示词已生成到 io/prompt.json
> ...

（后续流程相同）
```

---

## 9. 多轮对话 Memory 解决方案（参照 Hermes）

### 9.1 三层记忆架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Long-term Memory（持久化）                │
│  - session.json 持久化所有历史 turns                        │
│  - wiki 知识库存储重要信息                                  │
│  - 摘要：当对话过长时自动总结历史                            │
└─────────────────────────────────────────────────────────────┘
                              ↑
                              │ 自动加载
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Short-term Memory（内存）                 │
│  - 当前 session 的 turns 列表                              │
│  - 待处理的工具调用结果                                     │
│  - 当前任务的中间状态                                       │
└─────────────────────────────────────────────────────────────┘
                              ↑
                              │ 构建 prompt
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Context（发送给大模型）                 │
│  - Persona 系统提示词                                      │
│  - 相关 Memory 片段                                        │
│  - 当前轮次的对话历史                                       │
│  - 可用工具列表                                            │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 自动摘要机制

当 `turns` 数量超过 `summary_threshold`（默认 10）时：
1. Agent 调用大模型生成摘要
2. 摘要存入 `memory.summaries`
3. 旧的 turns 可被压缩或移除
4. 保持上下文完整但减少 token 消耗

### 9.3 Memory 操作接口

```python
class Memory:
    def add_turn(self, turn: dict)          # 添加一轮对话
    def get_conversation(self) -> list       # 获取对话历史
    def search(self, query: str) -> list     # 搜索记忆
    def summarize(self) -> str               # 生成摘要
    def load_from_session(self, session)     # 从 session 恢复
    def save_to_session(self, session)      # 保存到 session
```

---

## 10. 确认事项

- [x] 文件格式：JSON ✓
- [x] 架构：Hermes 风格（目录 + 核心逻辑）✓
- [x] 工具集：文件操作 + 命令执行 + Python 执行 + 文档知识库 ✓
- [x] 内网环境支持 ✓
- [x] 多轮对话 Memory 持久化 ✓

---

如设计OK，请回复确认，我将进入 Phase 2：编写实现计划。
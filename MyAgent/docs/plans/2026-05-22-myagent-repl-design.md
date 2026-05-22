# MyAgent v2 REPL 重构计划

**日期:** 2026-05-22
**目标:** 将 MyAgent 改造成人性化 REPL 交互循环

---

## 需求总结

1. `input.txt` 纯文本输入
2. `prompt.txt` 纯文本提示词（供用户复制到 LLM）
3. `response.txt` 纯文本粘贴（代码自动解析）
4. 每个步骤有中文提示
5. 工具执行显示 1/2/3 步骤
6. 多轮循环不退出
7. `quit` 在 input 层退出程序，其他时候 quit 取消任务回到 input 层
8. 任务完成后自动回到 input 层等新任务

---

## 改动文件清单

| 文件 | 改动 |
|------|------|
| `agent/loop_v2.py` | 重写 REPL 主循环，更新文件读写 |
| `run.bat` | 小调整提示文字 |

### 废弃文件（不再使用）

- `io/input.json` → 改用 `input.txt`
- `io/response.json` → 改用 `response.txt`
- `io/prompt.json` → 改用 `prompt.txt`
- `start.bat` → 可删除

---

## 核心数据结构

### 文件映射

```python
io_config = {
    "input_file": "io/input.txt",      # 用户写任务（纯文本）
    "prompt_file": "io/prompt.txt",      # 生成的提示词（纯文本）
    "response_file": "io/response.txt", # LLM 回复（纯文本粘贴）
    "session_file": "io/session.json",  # 会话持久化（保留）
    "tool_result_file": "io/tool_result.json" # 工具结果（保留）
}
```

---

## Task 1: 重写 parse_response - 支持纯文本 response

**验证标准:** `response.txt` 直接写入纯文本，解析后 content 正确

```python
def parse_response(raw: str) -> dict:
    # 纯文本 -> {"content": raw, "tool_calls": []}
    # JSON {"result": ...} -> {"content": result, "tool_calls": []}
    # JSON {"content": ...} -> 直接返回
    # JSON {"think": ..., "action": "tool_call", "tools": [...]} -> 转为 tool_calls 格式
    pass
```

### TDD 测试用例

```python
# test_response_parsing.py
assert parse_response("纯文本回复") == {"content": "纯文本回复", "tool_calls": []}
assert parse_response('{"result": "结果"}') == {"content": "结果", "tool_calls": []}
assert parse_response('{"content": "答案", "tool_calls": []}') == {"content": "答案", "tool_calls": []}
assert parse_response('{"think": "思考", "action": "tool_call", "tools": [{"tool": "file_read", "params": {"path": "a.txt"}}]}')["tool_calls"][0]["tool"] == "file_read"
```

---

## Task 2: 重写 prompt 生成 - 输出纯文本 prompt.txt

**验证标准:** `prompt.txt` 是可直接复制的纯文本，包含 LLM 输出格式说明

```python
def build_prompt_file(user_input: str, turn: int, tool_results: list) -> str:
    """生成纯文本格式的 prompt.txt"""
    content = f"""你是 MyAgent，一个智能助手。

【当前任务】(第 {turn} 轮)
{user_input}

【输出格式要求】
完成思考后，严格按以下格式返回（不要输出任何其他内容）:

# 需要工具时:
{{"think": "你的思考", "action": "tool_call", "tools": [{{"tool": "工具名", "params": {{"参数": "值"}}}}]}}

# 最终答案时:
{{"think": "你的思考", "action": "final", "answer": "你的回答"}}

【可用工具】
{tools_list}

【对话历史】
{conversation_history}
"""
    return content
```

---

## Task 3: 重写主 REPL 循环

**验证标准:** 完整流程跑通：input.txt → prompt.txt → response.txt → 执行 → 显示步骤 → 循环/完成

```python
def repl_main():
    """REPL 主循环"""
    while True:
        # 显示 header
        print_header()

        # 等待用户输入（文件输入或 quit）
        user_input = wait_for_input()
        if user_input == "quit":
            print("[退出] 再见！")
            break

        # 执行任务（可能多轮）
        run_task(user_input)
        # 任务完成后自动回到这里等新任务
```

### wait_for_input() 逻辑

```
显示: "请在 input.txt 写任务，输入 quit 退出"
用户: 写 input.txt，敲回车
  - 检查 input.txt 有内容
  - 读取内容
  - 清空 input.txt（或保留，用户自己管）
  - 返回任务内容
用户: 敲回车但 input.txt 为空
  - 继续等待
用户: 直接输入 "quit"（stdin） -> 返回 "quit"
```

### run_task() 逻辑

```
turn = 1
tool_results = None
while True:
    # 读取 response.txt（用户粘贴 LLM 回复后敲回车）
    prompt_file = build_prompt(...)
    save_prompt(prompt_file)
    print("[生成] 提示词已写入 prompt.txt，请复制到 LLM")

    # 等待用户粘贴回复
    print("[等待] 请把 LLM 回复粘贴到 response.txt，按回车继续...")
    user_response = wait_for_response()  # 敲回车时读取 response.txt
    if user_response == "quit":
        print("[取消] 当前任务已取消，回到等待输入")
        break

    # 解析 response
    parsed = parse_response(user_response)
    if parsed["action"] == "tool_call":
        execute_tools(parsed["tools"])  # 显示 1. 2. 3. 步骤
        turn += 1
        continue
    else:
        print_final_answer(parsed["answer"])
        break  # 回到 input 层
```

### execute_tools() 显示格式

```
[工具] 检测到 N 个工具，执行中...
  1. file_read: 读取 README.md ... OK
  2. shell_run: 执行 dir /b ... FAIL (文件不存在)
[完成] 工具执行完毕，继续第 2 轮...
```

---

## Task 4: 执行结果汇总与打包

1. 删除调试文件
2. 清理 __pycache__
3. 测试完整流程
4. 打包发送

---

## 风险点

1. **REPL stdin 输入冲突**: Windows 下 stdin 和文件读取混用可能有问题，需要用 `msvcrt` 或单独线程检测
2. **prompt.txt 编码**: 必须是 UTF-8，否则中文乱码
3. **多轮对话历史**: session.json 保留，确保多轮可继续

---

## 交付物

1. 重构后的 `agent/loop_v2.py`
2. 更新后的 `run.bat`
3. 最终 zip 包

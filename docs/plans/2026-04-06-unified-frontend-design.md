# 雷达智能脑统一前端 — 实施计划

## 目标
将自然语言对话与雷达 PPI 监控整合为统一界面，同时提供配置管理页面。

## 架构

```
用户浏览器
  └── /unified          → unified.html（统一前端）
  └── /api/agent/chat   → api.py 转发 → subprocess → radar-brain/run.py
  └── /api/state        → 雷达后端状态（已有）
  └── /api/*            → 其他雷达控制（已有）
```

---

## 任务清单

### Task 1：后端 /api/agent/chat 接口

**文件**：`E:\radarmonitornew\backend\api.py`

**操作**：
1. 添加 `ChatRequest` 模型：`{"message": str}`
2. 添加 `@app.post("/api/agent/chat")` 路由，handler 如下：
   ```python
   @app.post("/api/agent/chat")
   def agent_chat(req: ChatRequest):
       import subprocess
       try:
           result = subprocess.run(
               ["python", "E:/radar-brain/run.py", req.message],
               capture_output=True, text=True, timeout=120,
               cwd="E:/radar-brain"
           )
           return {"ok": True, "response": result.stdout or result.stderr}
       except subprocess.TimeoutExpired:
           return {"ok": False, "error": "超时（120秒）"}
   ```
3. 添加 `@app.get("/unified")` 返回 `unified.html`（FileResponse）

**验证**：`curl -X POST http://localhost:8000/api/agent/chat -H "Content-Type: application/json" -d "{\"message\":\"雷达状态如何\"}"` 返回 JSON

---

### Task 2：创建 unified.html（统一前端）

**文件**：`E:\radarmonitornew\frontend\unified.html`

**布局**（移动优先，参考现有深色主题）：

```
┌─────────────────────────────────┐
│ [雷达监控] [配置]    ← 顶部Tab  │
├─────────────────────────────────┤
│ 雷达监控Tab:                    │
│ ┌─────────────┬───────────────┐ │
│ │             │ 聊天对话框     │ │
│ │   PPI显示   │               │ │
│ │  (canvas)  │  消息气泡列表   │ │
│ │             │               │ │
│ │             │  [输入框][发送] │ │
│ └─────────────┴───────────────┘ │
├─────────────────────────────────┤
│ [雷达状态栏：功率|模式|目标数]   │
└─────────────────────────────────┘
```

**功能要求**：

1. **Tab 切换**：点击"雷达监控"/"配置"切换两个面板
2. **PPI 显示**：直接复用 `index.html` 中现有的 JS 变量和函数（`drawPPI`, `radarState`, `fetchState`, `calcPPI`），内联到 unified.html 中（不需要 fetch，独立运行）
3. **聊天面板**：
   - 消息气泡：用户消息右对齐（#00ff88背景），AI回复左对齐（#1a2a3a背景）
   - 发送方式：POST `/api/agent/chat` + `{"message": "用户文字"}`
   - 加载状态：发送时显示"思考中..."气泡
   - 响应后追加AI回复气泡
   - 回车键发送
4. **雷达状态栏**：显示 power/mode/track-count，250ms轮询 `/api/state`
5. **配置Tab**：
   - 大模型选择：下拉框（qwen3:4b-instruct / gemma4:e4b / gemma4:16k），保存到 `E:\radar-brain\config.yaml`
   - Skill 管理：列出 `E:\radar-brain\skills\` 子目录，勾选启用/禁用
   - 记忆同步：显示上次同步时间，手动触发 `python E:\radar-brain\scripts\sync_sessions_to_memory.py`
   - 保存配置：POST `/api/config/save`

**样式**：深色主题，#050a12 背景，#00ff88 主色，与现有 index.html 一致

**验证**：浏览器打开 `http://localhost:8000/unified`，切换Tab正常，聊天能收到AI回复

---

### Task 3：后端配置接口

**文件**：`E:\radarmonitornew\backend\api.py`

**操作**：
1. 添加 `@app.post("/api/config/save")` 接收配置，保存到 `E:\radar-brain\config.yaml`
2. 添加 `@app.get("/api/config")` 读取当前配置

---

## 实施顺序

1. Task 1（后端 chat 接口）→ 验证通过后
2. Task 3（配置接口）→ 
3. Task 2（unified.html）→ 验证通过后
4. 整体测试：打开 `/unified`，聊天说"把雷达切换到搜索模式"，验证雷达实际响应

## 约束

- 不修改 `index.html`
- 不修改 `E:\radar-brain\agent\` 下代码
- 子进程超时 120 秒

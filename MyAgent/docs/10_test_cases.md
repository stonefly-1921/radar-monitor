# MyAgent 自动化测试用例 - 10 个通用任务（增强版）

## 测试文件
- 测试脚本：`MyAgent/run_10_tests.py`
- 测试文档：`MyAgent/docs/10_test_cases.md`
- 代码修复：`MyAgent/agent/loop_v2.py`（parse_response 嵌套 JSON 修复）

---

## 10 个测试任务（增强版）

### 任务 1：计算任务
**目标**：测试 python_run 工具基础功能  
**任务**：请用 python_run 工具计算 1+1 等于几，结果直接输出  
**预期工具**：`python_run`  
**验证**：LLM 返回 `{"action": "final", "answer": "2"}`

---

### 任务 2：文件操作（多步骤）
**目标**：测试 file_list + file_read + python_run 组合  
**任务**：
1. 用 file_list 列出 MyAgent 目录下所有 .py 文件
2. 用 file_read 读取任意一个 .py 文件前 20 行
3. 用 python_run 统计该文件总行数
4. 输出文件路径和行数

**预期工具**：`file_list`, `file_read`, `python_run`

---

### 任务 3：弹道仿真（AFSIM 场景）
**目标**：测试 grep + file_read + python_run 综合弹道计算  
**任务**：
1. 用 grep 在 MyAgent 搜索 "fires" 或 "ballistic" 关键词的 .cpp/.py 文件
2. 用 file_read 读取找到的文件，分析弹道导弹参数
3. 用 python_run 计算：北京→台北弹道（经度差5.1°，纬度差14.9°，初速3000m/s，射角45°）
4. 输出：飞行时间、最大高度、射程

**预期工具**：`grep`, `file_read`, `python_run`  
**计算公式**：
- 水平射程 R = v₀² × sin(2θ) / g ≈ 918 km
- 最大高度 H = v₀² × sin²(θ) / (2g) ≈ 230 km
- 飞行时间 T = 2v₀ × sin(θ) / g ≈ 433 s

---

### 任务 4：代码审查
**目标**：测试 file_list + file_read + grep + python_run 完整代码分析流程  
**任务**：
1. file_list 列出 MyAgent/agent 目录下所有 .py 文件
2. 选取 2 个文件用 file_read 读取完整内容
3. grep 搜索每个文件中 "def " 所在行
4. python_run 统计：每个文件函数个数，总函数个数
5. 列出所有函数名及行号

**预期工具**：`file_list`, `file_read`, `grep`, `python_run`

---

### 任务 5：Wiki 操作
**目标**：测试 wiki_search + wiki_read + python_run 知识库查询  
**任务**：
1. wiki_search 搜索 "弹道导弹"
2. 查看至少 2 条搜索结果
3. wiki_read 读取其中一条详细内容
4. python_run 计算：射程1000km，速度2km/s，飞行时间 = 500s

**预期工具**：`wiki_search`, `wiki_read`, `python_run`

---

### 任务 6：文档撰写 ✨新增
**目标**：测试 python_run + file_write + file_read 文档生成流程  
**任务**：
1. python_run 执行代码生成 Markdown 测试报告
2. file_write 将报告写入 `MyAgent/io/test_report.txt`
3. file_read 读取验证文件已正确写入

**预期工具**：`python_run`, `file_write`, `file_read`  
**报告格式**：
```markdown
# 弹道导弹仿真测试报告

## 1. 任务概述
本报告记录弹道仿真测试结果。

## 2. 测试数据
- 发射点：北京（116.4°E, 39.9°N）
- 目标点：台北（121.5°E, 25°N）
- 初速度：3000 m/s
- 射角：45°

## 3. 计算结果
- 飞行时间：约 300 秒
- 最大高度：约 230 km
- 射程：约 350 km

## 4. 结论
测试完成，结果符合预期。
```

---

### 任务 7：表格处理 ✨新增
**目标**：测试 xlsx_create + xlsx_write + xlsx_read Excel 操作  
**任务**：
1. xlsx_create 创建 "test_data.xlsx"
2. xlsx_write 写入数据：
   - 表头：姓名, 年龄, 城市, 职业
   - 数据行：
     - 张三, 28, 北京, 工程师
     - 李四, 35, 上海, 设计师
     - 王五, 42, 深圳, 经理
3. xlsx_read 读取验证数据已正确写入

**预期工具**：`xlsx_create`, `xlsx_write`, `xlsx_read`  
**验证方式**：读取后检查表头和数据行数量是否正确

---

### 任务 8：Shell 命令
**目标**：测试 shell_run 系统命令执行  
**任务**：
1. shell_run 执行 `python --version` 查看 Python 版本
2. shell_run 执行 `dir C:\Users\15041\.openclaw\workspace\MyAgent` 查看目录
3. shell_run 执行 `powershell -Command "Get-Date"` 获取系统时间
4. python_run 计算：每天10次命令 × 100天 = 1000次

**预期工具**：`shell_run`, `python_run`

---

### 任务 9：多步骤工作流
**目标**：测试 file_list + python_run 多步骤数据统计  
**任务**：
1. file_list 列出 MyAgent/io 目录内容
2. 统计 .txt 文件数量
3. 统计 .json 文件数量
4. python_run 计算：.txt数量×10 + .json数量×5 = 总数
5. 输出每个步骤的结果

**预期工具**：`file_list`, `python_run`

---

### 任务 10：综合任务（文档+表格+代码）✨重点
**目标**：测试 xlsx + python_run + file_write/file_read 综合能力  
**任务**：

**步骤1 - 创建数据表格**：
- xlsx_create 创建 "comprehensive_test.xlsx"
- xlsx_write 写入：
  | 项目 | 数值 | 说明 |
  |------|------|------|
  | 圆周率 | 3.14159 | 圆周率常量 |
  | 自然对数 | 2.71828 | 自然常数 |
  | 黄金比例 | 1.61803 | 黄金分割 |

**步骤2 - 执行计算**：
- python_run 计算：
  - π × 10² = 314.159
  - e × 100 = 271.828
  - φ × 50 = 80.9015

**步骤3 - 生成 Markdown 报告**：
```markdown
# 综合测试报告

## 数据表格
已创建 comprehensive_test.xlsx，包含 3 行数据。

## 计算结果
- π × 10² = 314.159
- e × 100 = 271.828
- φ × 50 = 80.9015

## 结论
综合测试完成，所有计算结果已验证。
```

**步骤4 - 保存报告**：
- file_write 写入 `MyAgent/io/comprehensive_report.txt`

**步骤5 - 验证**：
- file_read 读取报告，确认数据正确

**预期工具**：`xlsx_create`, `xlsx_write`, `python_run`, `file_write`, `file_read`

---

## 运行测试

```bash
# 1. 确保 MyAgent UI 已启动
python C:\Users\15041\.openclaw\workspace\MyAgent\agent\ui.py

# 2. 运行 10 个测试
python C:\Users\15041\.openclaw\workspace\MyAgent\run_10_tests.py

# 3. 查看测试报告
# 测试结果自动保存在 session.json
```

---

## 已修复的问题

1. **UI 控件操作**：通过坐标位置识别控件，不再依赖硬编码 HWND
2. **API key 传递**：ui.py 的 `_start_repl_subprocess` 显式读取 User 环境变量
3. **嵌套 JSON 解析**：loop_v2.py 的 `parse_response` 增加二次解析，处理 LLM 返回的嵌套 JSON

---

## 验证结果查看

```python
import json
data = json.load(open(r'C:\Users\15041\.openclaw\workspace\MyAgent\io\session.json'))
turns = data['turns']
for t in turns[-10:]:
    print(f"Task: {t['input'][:60]}...")
    fa = t.get('final_answer', '')
    if fa:
        print(f"Result: {fa[:100]}...")
    print()
```

---

## 测试预期结果

| 任务 | 工具组合 | 预期完成时间 |
|------|---------|-------------|
| 1. 计算任务 | python_run | < 10s |
| 2. 文件操作 | file_list + file_read + python_run | < 30s |
| 3. 弹道仿真 | grep + file_read + python_run | < 60s |
| 4. 代码审查 | file_list + file_read + grep + python_run | < 60s |
| 5. Wiki 操作 | wiki_search + wiki_read + python_run | < 60s |
| 6. 文档撰写 | python_run + file_write + file_read | < 30s |
| 7. 表格处理 | xlsx_create + xlsx_write + xlsx_read | < 45s |
| 8. Shell 命令 | shell_run + python_run | < 30s |
| 9. 多步骤工作流 | file_list + python_run | < 30s |
| 10. 综合任务 | xlsx + python_run + file_write/file_read | < 120s |
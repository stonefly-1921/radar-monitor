# Python Debug Skill

## 简介
Python 调试技能，帮助定位和修复 Python 代码中的错误。

## 使用场景
- 修复 Python 代码的语法错误
- 定位运行时异常
- 调试逻辑错误

## 工具使用
- `python_run` - 运行 Python 代码并捕获错误
- `file_read` - 读取源代码
- `file_edit` - 修复代码问题

## 工作流程
1. 读取出错的 Python 文件
2. 使用 python_run 执行代码捕获错误信息
3. 分析错误类型和位置
4. 定位问题根因
5. 修复代码

## 常见错误处理
- `SyntaxError`: 检查括号、引号、缩进
- `NameError`: 检查变量名拼写和导入
- `TypeError`: 检查类型匹配
- `ImportError`: 检查模块路径
- `FileNotFoundError`: 检查文件路径

## 调试技巧
1. 逐行执行，关键位置加 print 语句
2. 使用 `python -m py_compile` 检查语法
3. 查看完整的错误堆栈信息
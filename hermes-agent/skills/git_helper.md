# Git Helper Skill

## 简介
Git 版本控制辅助技能，帮助执行常见的 Git 操作。

## 使用场景
- 查看 Git 状态
- 提交代码更改
- 查看历史记录
- 管理分支

## 工具使用
- `shell_run` - 执行 Git 命令

## 常用命令

### 查看状态
```
git status
git diff
```

### 提交更改
```
git add .
git commit -m "提交信息"
```

### 查看历史
```
git log --oneline -10
git log --graph --oneline
```

### 分支操作
```
git branch
git checkout <branch>
git merge <branch>
```

## 工作流程
1. 先查看 git status 了解当前状态
2. 根据需要执行 add/commit/pull/push 等操作
3. 使用 git log 查看提交历史
4. 确认操作结果

## 注意事项
- 提交前先确认要提交的文件
- 写清楚提交信息
- push 前先 pull 合并
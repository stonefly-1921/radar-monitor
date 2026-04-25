# 微信聊天记录聚类（BERTopic）

## 任务

对微信聊天记录进行主题聚类、压缩，生成会话摘要。

## 数据

- 来源：`wxdump_work/wshjustin/`（pywxdump 提取）
- 位置：`C:\Users\15041\.openclaw\workspace\wxdump_work\wshjustin\`

## 状态

**聚类任务未完成**——被 BERTopic model.save() OOM 阻塞。

---

## ⚠️ BERTopic OOM 问题（用户提供，2026-04-25 23:04）

**症状**：聚类完成后保存模型时 OOM。

**根因**：
- BERTopic.save() 序列化整个模型：123k×384 embedding 矩阵（~190MB）+ 全部原始文本 + UMAP + HDBSCAN 参数
- embedding 矩阵在 UMAP 后未释放，一直占用内存

**解决方案**：
1. 每步监控内存峰值（psutil）
2. UMAP 后释放 embedding，HDBSCAN 后释放 UMAP
3. 分步保存，不使用 BERTopic 一键 save()

---

## 相关文件

- `wxdump_work/wxdump.log` - pywxdump 运行日志
- `get_wechatmsg*.py` - 微信消息提取脚本

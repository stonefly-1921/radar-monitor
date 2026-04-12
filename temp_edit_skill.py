# -*- coding: utf-8 -*-
import shutil

src = r'E:\radar-brain-github\agent\skills\radar_command\SKILL.md'
bak = src + '.bak2'
shutil.copy2(src, bak)

with open(src, 'r', encoding='utf-8') as f:
    content = f.read()

# ── 任务1：强化输出规范 ──
old_reply_format = (
    "程序字段名。\n\n## 工具定义"
)
new_reply_format = (
    "程序字段名。\n\n"
    "## 工具执行结果的回复规范\n"
    "调用工具后，回复用户时必须：\n"
    "1. 只提取 `output` 字段的自然语言内容进行回复\n"
    "2. 禁止把 `{\"success\": ..., \"output\": ..., \"data\": ...}` 这类原始返回结构直接暴露给用户\n"
    "3. 禁止在回复中出现 `{}`、`'success'`、`'output'`、`message`、`error` 等程序字段名\n\n"
    "## 工具定义"
)

if old_reply_format in content:
    content = content.replace(old_reply_format, new_reply_format, 1)
    print("Task1_OK")
else:
    print("Task1_FAIL")

# ── 任务2：增加定方位监视规则 ──
old_rule_z = (
    "### 规则Z：开机全方位搜索后识别所有目标（复合指令）\n"
    "当用户指令同时包含「开机」和「识别」（如\"开机全方位搜索并识别\"、\"开机并识别所有目标\"），执行以下步骤序列：\n"
    "```\n"
    "1. [power_on] → 开机"
)
new_rule_5_and_z = (
    "### 规则5：定方位监视\n"
    "当用户指令包含\"定方位\"、\"固定方位\"、\"指向方位\"或\"在方位X度\"时（X为数字），执行以下步骤：\n"
    "```\n"
    "1. [get_radar_status] → 获取当前工作模式\n"
    "2. IF mode == \"spin\"（转动模式）\n"
    "   THEN [set_mode(mode=stop)] → 先切换为停转模式\n"
    "3. [set_steer(azimuth=<用户指定方位>, elevation=0)]\n"
    "```\n"
    "**重要**：转动模式（spin）下无法调整天线指向，必须先切停转才能执行定方位。\n\n"
    "### 规则Z：开机全方位搜索后识别所有目标（复合指令）\n"
    "当用户指令同时包含「开机」和「识别」（如\"开机全方位搜索并识别\"、\"开机并识别所有目标\"），执行以下步骤序列：\n"
    "```\n"
    "1. [power_on] → 开机"
)

if old_rule_z in content:
    content = content.replace(old_rule_z, new_rule_5_and_z, 1)
    print("Task2_OK")
else:
    print("Task2_FAIL")

with open(src, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done_Backup:" + bak)

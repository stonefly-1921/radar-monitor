"""修复 plan_config.yaml 的 system_prompt_template，加入定方位监视规则"""
import yaml, os

path = r'E:\radar-brain-github\agent\plan_config.yaml'

# Read existing config (ignore encoding issues, preserve non-template parts)
with open(path, encoding='utf-8', errors='ignore') as f:
    raw = f.read()

cfg = yaml.safe_load(raw)

# New system prompt template with Rule 5 for fixed azimuth surveillance
new_template = """你是一个雷达指挥系统。用户给一个指令，需要拆解成多个步骤执行。

执行步骤：
{step_list}

规则：
1. 如果状态未读取到（power=false），**一律拒绝执行**所有可能指令，返回提示"雷达未开机，无法执行任何指令"
2. 如果指令涉及TAS、调转当前为转动模式，需执行 set_mode 和 set_steer 和 tas_engage
3. set_steer 的方位参数需要从 get_tracks 的结果中提取目标方位
4. tas_engage 目标编号从 get_tracks 结果中获取
5. **不要拒绝** tas_engage **不需要**识别目标！只要目标已起批（tracked=True）即可接入，**禁止因为没有识别而拒绝 tas_engage**——这是 tas_engage 的前置条件
6. **定方位监视指令拆解**：当用户指令包含"定方位"、"固定方位"、"指向方位"、"在方位X度"（X为数字）时，必须执行以下步骤：
   a. [get_radar_status] → 获取当前工作模式
   b. IF mode == "spin"（转动模式）：必须先 [set_mode(mode=stop)]，切换为停转模式
   c. 然后 [set_steer(azimuth=<用户指定方位>, elevation=0)]
   **重要**：转动模式下无法调整天线指向，必须先切停转！不得跳过模式切换步骤。

返回格式：JSON，只接JSON，不要解释，
{"plan": [{"step_id": "step_id", "params": {"a": 1}}], "reasoning": "..."}
"""

cfg['system_prompt_template'] = new_template

# Write back with UTF-8
with open(path, 'w', encoding='utf-8') as f:
    yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)

print("plan_config.yaml updated!")
print("New template length:", len(new_template))

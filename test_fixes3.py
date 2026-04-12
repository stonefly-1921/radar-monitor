"""直接测试 skill.execute('tas_engage') 在雷达关机情况下的行为"""
import sys
sys.path.insert(0, r'E:\radar-brain-github\agent')

from skills.radar_command.skill import RadarSkill
from skills.radar_command.simulator_wrapper import get_simulator
import json

# 重置
sim = get_simulator()
sim.set_power(False)
sim.reset()
print(f"雷达状态: power={sim.get_state_snapshot().get('power')}")

# 实例化 skill
skill = RadarSkill()

# 测试1: 雷达关机时 tas_engage 应该自动开机
print("\n=== 测试: 雷达关机时 tas_engage ===")
result = skill.execute("tas_engage", {"target_id": 1, "data_rate": 1}, {})
print(f"result: {result}")
print(f"雷达状态 after: power={sim.get_state_snapshot().get('power')}")

# 测试2: 数据率设置（tas_set_data_rate）
print("\n=== 测试: tas_set_data_rate ===")
# 先接入TAS
sim.set_power(True)
sim.set_mode("stop")
sim.set_steer(azimuth=45, elevation=0)
ok, err = sim.tas_engage(1, 1)
print(f"tas_engage: ok={ok}, err={err}")
# 再调数据率
result2 = skill.execute("tas_set_data_rate", {"target_id": 1, "data_rate": 10}, {})
print(f"tas_set_data_rate result: {result2}")

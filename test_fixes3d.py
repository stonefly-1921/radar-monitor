"""直接测试 skill.execute('tas_engage') 雷达关机行为"""
import sys, os
sys.path.insert(0, r'E:\radar-brain-github')
sys.path.insert(0, r'E:\radar-brain-github\agent')
sys.path.insert(0, r'E:\radar-brain-github\backend')

from skills.radar_command.skill import RadarCommandSkill
from backend.simulator import get_simulator

# 重置
sim = get_simulator()
sim.set_power(False)
sim.reset_simulation()
print(f"雷达初始状态: power={sim.get_state_snapshot().get('power')}")

# 实例化 skill
skill = RadarCommandSkill()

# 测试1: 雷达关机时 tas_engage → 应该自动开机（不需要手动开机）
print("\n=== 测试: 雷达关机时 tas_engage ===")
result = skill.execute("tas_engage", {"target_id": 1, "data_rate": 1}, {})
print(f"result: success={result.success} output={result.output!r} error={result.error!r}")
state = sim.get_state_snapshot()
print(f"雷达 after: power={state.get('power')} mode={state.get('mode')}")

# 测试2: 数据率设置
print("\n=== 测试: tas_set_data_rate ===")
sim.set_power(True)
sim.set_mode("stop")
sim.set_steer(azimuth=45, elevation=0)
ok, err = sim.tas_engage(1, 1)
print(f"tas_engage: ok={ok}")
result2 = skill.execute("tas_set_data_rate", {"target_id": 1, "data_rate": 10}, {})
print(f"tas_set_data_rate: success={result2.success} output={result2.output!r}")

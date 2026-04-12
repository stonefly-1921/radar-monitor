"""直接测试 Orchestrator.receive()"""
import sys, os, asyncio
sys.path.insert(0, r'E:\radar-brain-github')
sys.path.insert(0, r'E:\radar-brain-github\agent')
sys.path.insert(0, r'E:\radar-brain-github\backend')

import json

# 重置雷达状态
from backend.simulator import get_simulator
sim = get_simulator()
sim.set_power(False)
sim.reset_simulation()

print("雷达初始: power=" + str(sim.get_state_snapshot()["power"]))

# 加载 orchestrator
from agent_loop import AgentLoop
loop = AgentLoop()

import time
t0 = time.time()
result = loop.chat("TAS跟踪1号目标", session_id="test_orch")
elapsed = time.time() - t0
print("耗时: " + str(elapsed) + "s")
print("Result: " + str(result)[:500])
print("雷达 after: power=" + str(sim.get_state_snapshot()["power"]))
print("TAS: " + str(sim.get_state_snapshot().get("tas_tracking", {})))

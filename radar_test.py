# radar-brain 功能测试脚本
import requests
import json
import time

BASE = "http://localhost:8000"

def chat(msg, session="test"):
    r = requests.post(f"{BASE}/api/agent/chat", json={"message": msg, "session_id": session}, timeout=60)
    return r.json()

def state():
    r = requests.get(f"{BASE}/api/state", timeout=5)
    return r.json()

def get_tasks():
    r = requests.get(f"{BASE}/api/async_tasks", timeout=5)
    return r.json()

print("=" * 60)
print("测试 1：开机并全方位搜索")
print("=" * 60)
resp1 = chat("开机并全方位搜索")
print(f"回复: {resp1}")
time.sleep(3)
s1 = state()
print(f"雷达状态: power={s1['power']}, mode={s1['mode']}")

print()
print("=" * 60)
print("测试 2：反馈当前掌握的目标数")
print("=" * 60)
resp2 = chat("目前起批几个目标？")
print(f"回复: {resp2}")
s2 = state()
print(f"雷达状态: mode={s2['mode']}, targets_detected_count={sum(1 for t in s2['targets'] if t.get('detected'))}")

print()
print("=" * 60)
print("测试 3：对某批目标进行TAS跟踪（转动模式应拒绝）")
print("=" * 60)
resp3 = chat("对1号目标进行跟踪")
print(f"回复: {resp3}")

print()
print("=" * 60)
print("测试 4：回复停转并对某批目标进行跟踪")
print("=" * 60)
resp4 = chat("先停转，然后对1号目标进行跟踪")
print(f"回复: {resp4}")
time.sleep(3)
s4 = state()
print(f"雷达状态: mode={s4['mode']}, tas_tracking={s4.get('tas_tracking')}")

print()
print("=" * 60)
print("测试 5：对某批目标跟踪数据率提高到10赫兹")
print("=" * 60)
resp5 = chat("把1号目标的跟踪数据率改成10赫兹")
print(f"回复: {resp5}")
time.sleep(2)
s5 = state()
print(f"雷达状态: tas_tracking={s5.get('tas_tracking')}")

print()
print("=" * 60)
print("测试 6：对某批目标进行识别")
print("=" * 60)
resp6 = chat("对1号目标进行识别")
print(f"回复: {resp6}")
time.sleep(5)
s6 = state()
print(f"雷达状态: target1_identified={s6['targets'][0].get('identified_model')}")

print()
print("=" * 60)
print("测试 7：当前有哪些类型的已识别目标")
print("=" * 60)
resp7 = chat("当前有哪些类型的已识别目标？")
print(f"回复: {resp7}")

print()
print("=" * 60)
print("测试 8：对所有目标进行识别（转动模式，应先停转）")
print("=" * 60)
resp8 = chat("请对所有目标进行识别，并上报识别结果")
print(f"回复: {resp8}")

print()
print("=" * 60)
print("测试 9：多目标同时TAS跟踪")
print("=" * 60)
resp9 = chat("请对1号、2号、3号目标转TAS跟踪")
print(f"回复: {resp9}")
time.sleep(3)
s9 = state()
print(f"雷达状态: mode={s9['mode']}, tas_tracking={s9.get('tas_tracking')}")

print()
print("=" * 60)
print("测试 10：对F22目标转TAS跟踪")
print("=" * 60)
resp10 = chat("请对F22这样的目标进行TAS跟踪")
print(f"回复: {resp10}")

print()
print("=" * 60)
print("测试 11：对第一象限的目标转跟踪")
print("=" * 60)
resp11 = chat("请对第一象限的目标转跟踪")
print(f"回复: {resp11}")
s11 = state()
print(f"雷达状态: mode={s11['mode']}, tas_tracking={s11.get('tas_tracking')}")

print()
print("=" * 60)
print("测试 12：跟踪了哪些目标，数据率多少")
print("=" * 60)
resp12 = chat("当前跟踪了哪些目标？每个目标的数据率是多少？")
print(f"回复: {resp12}")

print()
print("全部测试完成")

"""完整修复验证 - qwen3:4b-instruct 模型"""
import requests, time, json

BASE = "http://localhost:8000"

def reset():
    requests.post(f"{BASE}/api/simulation/reset", json={}, timeout=5)
    requests.post(f"{BASE}/api/power", json={"state": "off"}, timeout=5)
    r = requests.get(f"{BASE}/api/state", timeout=5)
    return r.json()

print("=== 完整修复验证 ===\n")

# Test 1: 雷达关机 + TAS指令 → 应该自动开机 + TAS接入
print("【测试1】雷达关机 + TAS跟踪1号目标 → 应自动开机")
state = reset()
print(f"初始状态: power={state['power']} mode={state['mode']}")

t0 = time.time()
r = requests.post(f"{BASE}/api/agent/chat",
    json={"message": "TAS跟踪1号目标", "session_id": f"t{int(t0)}"},
    timeout=60)
elapsed = time.time() - t0

print(f"耗时: {elapsed:.0f}s")
try:
    resp = r.json()
    reply = resp.get("reply", "")
    print(f"回复: {reply[:300]}")
except:
    print(f"raw: {r.text[:300]}")

state_after = requests.get(f"{BASE}/api/state", timeout=5).json()
print(f"雷达状态 after: power={state_after['power']} mode={state_after['mode']}")
print()

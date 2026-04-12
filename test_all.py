"""完整测试 - qwen3:4b-instruct + 自动开机修复"""
import requests, time, json

BASE = "http://localhost:8000"

def reset():
    requests.post(f"{BASE}/api/simulation/reset", json={}, timeout=5)
    requests.post(f"{BASE}/api/power", json={"state": "off"}, timeout=5)
    r = requests.get(f"{BASE}/api/state", timeout=5)
    return json.loads(r.text)

print("=== 修复验证（qwen3:4b-instruct）===\n")

# Test 1: 雷达关机 + TAS指令
print("【测试1】雷达关机 + TAS跟踪1号目标 → 应自动开机")
state = reset()
print(f"初始: power={state['power']}")

t0 = time.time()
r = requests.post(f"{BASE}/api/agent/chat",
    json={"message": "TAS跟踪1号目标", "session_id": f"t{int(t0)}"},
    timeout=180)
elapsed = time.time() - t0

print(f"耗时: {elapsed:.0f}s")
try:
    resp = r.json()
    reply = resp.get("reply", "")
    print(f"回复: {reply[:300]}")
except:
    print(f"raw: {r.text[:300]}")

state_after = requests.get(f"{BASE}/api/state", timeout=5)
state_after = json.loads(state_after.text)
print(f"雷达: power={state_after['power']} mode={state_after['mode']}")
print(f"TAS: {state_after.get('tas_tracking', {})}")

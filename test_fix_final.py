"""完整修复验证"""
import requests, time, json

BASE = "http://localhost:8000"

def reset():
    requests.post(BASE + "/api/simulation/reset", json={}, timeout=5)
    requests.post(BASE + "/api/power", json={"state": "off"}, timeout=5)
    return json.loads(requests.get(BASE + "/api/state", timeout=5).text)

print("=== 完整修复验证 ===\n")

# 测试1: 雷达关机 + TAS
print("【测试1】雷达关机 + TAS跟踪1号目标")
state = reset()
print("初始: power=" + str(state["power"]))

t0 = time.time()
r = requests.post(BASE + "/api/agent/chat",
    json={"message": "TAS跟踪1号目标", "session_id": "fix1"},
    timeout=60)
elapsed = time.time() - t0

print("耗时: " + str(elapsed) + "s")
try:
    resp = r.json()
    reply = resp.get("reply", "")
    print("回复: " + reply[:300])
except:
    print("raw: " + r.text[:300])

state2 = json.loads(requests.get(BASE + "/api/state", timeout=5).text)
print("雷达: power=" + str(state2["power"]) + " mode=" + state2["mode"])
print("TAS跟踪: " + str(state2.get("tas_tracking", {})))

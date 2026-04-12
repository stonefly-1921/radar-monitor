"""通过飞书走 LLM 编排路径测试（包含'上报'触发LLM条件）"""
import requests, time

BASE = "http://localhost:8000"

def reset():
    requests.post(f"{BASE}/api/simulation/reset", json={}, timeout=5)
    requests.post(f"{BASE}/api/power", json={"state": "off"}, timeout=5)
    r = requests.get(f"{BASE}/api/state", timeout=5)
    return r.json()

print("=== 测试: 雷达关机 + TAS上报 → 应该走LLM编排 → 自动开机 ===")
state = reset()
print(f"初始: power={state['power']} mode={state['mode']}")

# 包含 TAS + 上报 → 触发 LLM 编排
t0 = time.time()
r = requests.post(f"{BASE}/api/agent/chat",
    json={"message": "TAS跟踪1号目标并上报状态", "session_id": f"llm{int(t0)}"},
    timeout=150)
elapsed = time.time() - t0
print(f"耗时: {elapsed:.0f}s")
print(f"状态: {r.status_code}")
try:
    resp = r.json()
    print(f"回复: {resp.get('reply', resp.get('message', ''))[:400]}")
except:
    print(f"raw: {r.text[:400]}")

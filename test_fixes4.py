"""通过飞书 session 运行修复验证"""
import requests, time, json

BASE = "http://localhost:8000"

def reset():
    requests.post(f"{BASE}/api/simulation/reset", json={}, timeout=5)
    requests.post(f"{BASE}/api/power", json={"state": "off"}, timeout=5)
    r = requests.get(f"{BASE}/api/state", timeout=5)
    return r.json()

print("=== 测试: 雷达关机时 TAS 指令 ===")
state = reset()
print(f"初始: power={state['power']} mode={state['mode']}")

# 通过飞书 chat 接口（OpenClaw 的 radar_command skill）
# 飞书 session 应该用 MiniMax 模型，比 qwen2.5 快
t0 = time.time()
r = requests.post(f"{BASE}/api/feishu/chat",
    json={"message": "TAS跟踪1号目标", "session_id": f"fix{int(t0)}"},
    timeout=90)
elapsed = time.time() - t0
print(f"耗时: {elapsed:.0f}s")
print(f"状态: {r.status_code}")
try:
    resp = r.json()
    print(f"回复: {resp.get('reply', resp.get('message', ''))[:400]}")
except:
    print(f"raw: {r.text[:400]}")

"""完整 unified agent 测试"""
import requests, time, sys

BASE = "http://localhost:8000"

def step(name, fn):
    t0 = time.time()
    try:
        r = fn()
        print(f"[{time.time()-t0:.1f}s] {name}: OK - {str(r)[:100]}")
        return r
    except Exception as e:
        print(f"[{time.time()-t0:.1f}s] {name}: FAILED - {e}")
        return None

# 1. 开机
print("\n=== 开机测试 ===")
step("state", lambda: requests.get(f"{BASE}/api/state", timeout=5))
step("power_on", lambda: requests.post(f"{BASE}/api/power", json={"state": "on"}, timeout=10))

# 2. 全方位搜索
print("\n=== 发送雷达指令 ===")
t0 = time.time()
r = requests.post(f"{BASE}/api/agent/chat",
    json={"message": "全方位搜索", "session_id": "test"},
    timeout=120)
elapsed = time.time()-t0
print(f"  Total: {elapsed:.1f}s, status={r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"  Reply: {data.get('reply', '')[:200]}")
else:
    print(f"  Error: {r.text[:200]}")

# 3. 状态查询
print("\n=== 状态查询 ===")
step("state", lambda: requests.get(f"{BASE}/api/state", timeout=5))

sys.exit(0)

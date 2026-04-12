"""验证 MiniMax 权限错误触发条件"""
import requests, time

BASE = "http://localhost:8000"

tests = [
    "全方位搜索",
    "重点关注第一象限",
    "在方位45度进行定方位监视",
    "方位45度定方位监视",
    "定方位监视",
    "重点关注第二象限",
]

for msg in tests:
    requests.post(BASE+"/api/simulation/reset", json={}, timeout=5)
    requests.post(BASE+"/api/power", json={"state": "on"}, timeout=5)
    t0 = time.time()
    r = requests.post(BASE+"/api/agent/chat", json={"message": msg, "session_id": "minimax_test"}, timeout=60)
    elapsed = time.time() - t0
    reply = r.json().get("reply", "")[:80] if r.status_code == 200 else f"HTTP {r.status_code}"
    is_perm_error = "权限" in reply or "permission" in reply.lower()
    status = "PERM_ERR" if is_perm_error else "OK"
    print(f"[{status}] {msg[:20]:20s} | {elapsed:5.1f}s | {reply[:60]}")

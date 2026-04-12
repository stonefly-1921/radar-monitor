"""完整修复验证"""
import requests, time, json

BASE = "http://localhost:8000"

def chat(message, session="test_fix", timeout=120):
    t0 = time.time()
    try:
        r = requests.post(f"{BASE}/api/agent/chat",
            json={"message": message, "session_id": session},
            timeout=timeout)
        return time.time()-t0, r.status_code, r.json().get("reply","")[:300]
    except Exception as e:
        return time.time()-t0, "error", str(e)

def reset():
    requests.post(f"{BASE}/api/simulation/reset", json={}, timeout=5)

print("=== Fix 1: tasEngage 不需要识别 ===")
reset()
_, code, reply = chat("对2号目标接入TAS", timeout=120)
print(f"  耗时:{_:.0f}s 状态:{code}")
print(f"  回复: {reply}")
print()

print("=== Fix 2: 雷达未开机时 tasEngage 自动开机 ===")
reset()
# 确保雷达是关机状态
r = requests.post(f"{BASE}/api/power", json={"state": "off"}, timeout=5)
print(f"  雷达当前: {r.json()}")
_, code, reply = chat("TAS跟踪1号目标", session="test_fix2", timeout=120)
print(f"  耗时:{_:.0f}s 状态:{code}")
print(f"  回复: {reply}")

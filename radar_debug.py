import requests
import time
import json

BASE = "http://localhost:8000"

def chat(msg, session="debug"):
    r = requests.post(f"{BASE}/api/agent/chat", json={"message": msg, "session_id": session}, timeout=60)
    return r.json()

def state():
    r = requests.get(f"{BASE}/api/state", timeout=5)
    return r.json()

# Reset simulation first
requests.post(f"{BASE}/api/simulation/reset", timeout=5)

# Test: send "开机" via agent
print("=== Test: Agent处理'开机' ===")
r = chat("开机")
print(f"回复: {r['reply'][:200] if isinstance(r, dict) else str(r)[:200]}")

# Check state immediately
s = state()
print(f"雷达状态: power={s['power']}, mode={s['mode']}")

# Also check via API directly
r2 = requests.post(f"{BASE}/api/power", json={"state": "on"}, timeout=5)
print(f"\n直接API开机: {r2.json()}")
s2 = state()
print(f"直接API后状态: power={s2['power']}, mode={s2['mode']}")

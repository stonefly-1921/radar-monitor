"""验证两个修复"""
import requests, time

BASE = "http://localhost:8000"

# Fix 1: tas_set_data_rate API endpoint
print("=== Fix 1: tas_setDataRate API ===")
r = requests.post(f"{BASE}/api/power", json={"state": "on"}, timeout=5)
print(f"power_on: {r.json()}")
r = requests.post(f"{BASE}/api/tasSetDataRate", json={"target_id": 1, "data_rate": 10}, timeout=5)
print(f"tasSetDataRate: {r.json()}")

# Fix 2: orchestrator with fresh state - test tas_engage flow
print("\n=== Fix 2: orchestrator tas flow ===")
r = requests.post(f"{BASE}/api/agent/chat",
    json={"message": "对1号目标接入TAS", "session_id": "fix_test"},
    timeout=60)
print(f"tas engage chat: {r.status_code}")
print(f"reply: {r.json().get('reply', '')[:200]}")

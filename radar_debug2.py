import requests
import json

BASE = "http://localhost:8000"

# Test: send "开机" via agent
r = requests.post(f"{BASE}/api/agent/chat", json={"message": "开机", "session_id": "debug2"}, timeout=60)
print(f"Status: {r.status_code}")
print(f"Response: {json.dumps(r.json(), ensure_ascii=False, indent=2)}")

# Check state
s = requests.get(f"{BASE}/api/state", timeout=5).json()
print(f"\nRadar state: power={s['power']}, mode={s['mode']}")

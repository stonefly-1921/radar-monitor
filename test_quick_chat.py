"""快速测试 chat 流程"""
import requests, time

BASE = "http://localhost:8000"

print("=== 1. test_llm ===")
t0 = time.time()
r = requests.get(f"{BASE}/api/test/llm", timeout=15)
print(f"  [{time.time()-t0:.1f}s] {r.json()}")

print("\n=== 2. test_orchestrator ===")
t0 = time.time()
r = requests.post(f"{BASE}/api/test/orchestrator", json={"message": "开机"}, timeout=15)
print(f"  [{time.time()-t0:.1f}s] {r.json()}")

print("\n=== 3. /api/agent/chat ===")
t0 = time.time()
r = requests.post(f"{BASE}/api/agent/chat",
    json={"message": "你好", "session_id": "test"},
    timeout=60)
print(f"  [{time.time()-t0:.1f}s] status={r.status_code}")
print(f"  {str(r.text)[:300]}")

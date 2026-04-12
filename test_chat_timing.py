"""分步测试 chat 流程"""
import requests, time, sys

BASE = "http://localhost:8000"

def step(name, fn):
    t0 = time.time()
    try:
        r = fn()
        print(f"[{time.time()-t0:.1f}s] {name}: OK")
        return r
    except Exception as e:
        print(f"[{time.time()-t0:.1f}s] {name}: FAILED - {e}")
        return None

# Step 1: state
step("state", lambda: requests.get(f"{BASE}/api/state", timeout=5))

# Step 2: power on
step("power_on", lambda: requests.post(f"{BASE}/api/radar/power", json={"power": True}, timeout=5))

# Step 3: test llm (direct)
t0 = time.time()
r = step("test_llm", lambda: requests.get(f"{BASE}/api/test/llm", timeout=10))
if r: print("  LLM result:", str(r)[:100])

# Step 4: test orchestrator
t0 = time.time()
r = step("test_orch", lambda: requests.post(f"{BASE}/api/test/orchestrator", json={"message": "开机"}, timeout=30))
if r: print("  Orch result:", str(r)[:200])

print("\n--- Now trying full chat (60s timeout) ---")
t0 = time.time()
try:
    r = requests.post(f"{BASE}/api/agent/chat",
        json={"message": "开机", "session_id": "test"},
        timeout=60)
    print(f"[{time.time()-t0:.1f}s] chat: {r.status_code} - {str(r.text)[:200]}")
except Exception as e:
    print(f"[{time.time()-t0:.1f}s] chat FAILED: {e}")

sys.exit(0)

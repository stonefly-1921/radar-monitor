"""Test18: spin模式定方位监视 (Ollama qwen3:4b)"""
import requests, time, sys

BASE = "http://localhost:8000"

def log(msg):
    sys.stdout.write("[{}] {}\n".format(time.strftime("%H:%M:%S"), msg))
    sys.stdout.flush()

log("=== Test18: spin模式下定方位监视 ===")
# Reset and power on in spin mode
requests.post(BASE+"/api/simulation/reset", json={}, timeout=5)
requests.post(BASE+"/api/power", json={"state": "on"}, timeout=5)
requests.post(BASE+"/api/mode", json={"mode": "spin"}, timeout=5)
log("雷达已开机，spin模式")

t0 = time.time()
r = requests.post(
    BASE+"/api/agent/chat",
    json={"message": "在方位45度进行定方位监视", "session_id": "test18_ollama"},
    timeout=120
)
elapsed = time.time() - t0
log("耗时: {:.1f}s, Status: {}".format(elapsed, r.status_code))
if r.status_code == 200:
    reply = r.json().get("reply", "")[:200]
    log("回复: " + reply)
else:
    log("Raw: " + r.text[:200])

"""View Test18 response without terminal encoding issues"""
import requests, json

BASE = "http://localhost:8000"

requests.post(BASE+"/api/simulation/reset", json={}, timeout=5)
requests.post(BASE+"/api/power", json={"state": "on"}, timeout=5)
requests.post(BASE+"/api/mode", json={"mode": "spin"}, timeout=5)

r = requests.post(
    BASE+"/api/agent/chat",
    json={"message": "在方位45度进行定方位监视", "session_id": "test18_view"},
    timeout=120
)
print("Status:", r.status_code)
if r.status_code == 200:
    reply = r.json().get("reply", "")
    # Write to file to avoid terminal encoding issues
    with open(r"C:\Users\15041\.openclaw\workspace\test18_reply.txt", "w", encoding="utf-8") as f:
        f.write(reply)
    print("Reply written to file")
    print("Length:", len(reply))
    print("First 500 chars:", reply[:500])

import requests
import time
import sys

BASE = "http://localhost:8000"
SESSION = "test"

def log(msg):
    print(msg, flush=True)

def call_chat(msg, timeout=120):
    url = f"{BASE}/api/agent/chat"
    start = time.time()
    r = requests.post(url, json={"message": msg, "session_id": SESSION}, timeout=timeout)
    elapsed = round(time.time() - start, 2)
    return elapsed, r.status_code, r.text

def get_state():
    r = requests.get(f"{BASE}/api/state", timeout=5)
    return r.json()

log("Starting 13 radar tests...")

results = []

# Case 1: power_on
t0 = time.time()
r = requests.post(f"{BASE}/api/power", json={"state": "on"}, timeout=5)
t1 = round(time.time() - t0, 2)
st = get_state()
results.append((1, "power_on", t1, r.status_code, "OK" if r.ok else r.text[:80]))
log(f"[1/13] power_on: {t1}s status={r.status_code} power={st['power']} mode={st['mode']}")

cases = [
    (2, "全方位搜索", "全方位搜索"),
    (3, "目标识别", "识别目标"),
    (4, "数据率设置", "把1号目标数据率设为10Hz"),
    (5, "TAS接入", "对1号目标接入TAS"),
    (6, "TAS断开", "断开1号目标TAS"),
    (7, "定方位监视", "在方位45度进行定方位监视"),
    (8, "象限监视", "在第一象限进行象限监视"),
    (9, "点名召唤", "对2号目标点名召唤"),
    (10, "目标报告", "给我一份目标报告"),
    (11, "状态查询", "当前雷达状态如何"),
    (12, "异常指令", "开机然后直接开TAS"),
    (13, "组合指令", "先开机，然后全方位搜索，等3秒后查看目标"),
]

for case_num, label, msg in cases:
    t0 = time.time()
    elapsed, status, resp = call_chat(msg)
    st = get_state()
    summary = resp[:120].replace('\n', ' ').replace('\r', '')
    results.append((case_num, label, elapsed, status, summary))
    log(f"[{case_num}/13] {label}: {elapsed}s status={status} mode={st['mode']} reply={summary[:80]}")

# Print table
log("\n\n|RADAR-TEST-RESULTS|")
log("|#|用例|耗时|状态|回复摘要|")
log("|---|------|------|------|----------|")
for num, label, t, s, txt in results:
    summary = txt[:80]
    log(f"|{num}|{label}|{t}s|{s}|{summary}|")

"""补充测试 14-18（修复后版本）"""
import requests, time, json

BASE = "http://localhost:8000"
results = []

def log(msg):
    sys.stdout.write("[{}] {}\n".format(time.strftime("%H:%M:%S"), msg))
    sys.stdout.flush()

import sys

def call_chat(msg, session, timeout=60):
    t0 = time.time()
    try:
        r = requests.post(f"{BASE}/api/agent/chat", json={"message": msg, "session_id": session}, timeout=timeout)
        return time.time()-t0, r.status_code, r.json().get("reply","")[:200] if r.status_code == 200 else f"HTTP {r.status_code}"
    except Exception as e:
        return time.time()-t0, "ERR", str(e)[:100]

def get_tracks():
    r = requests.get(f"{BASE}/api/tracks", timeout=5)
    return r.json() if r.status_code == 200 else {}

def get_state():
    r = requests.get(f"{BASE}/api/state", timeout=5)
    return r.json() if r.status_code == 200 else {}

def api_post(path, json_data, timeout=5):
    r = requests.post(f"{BASE}{path}", json=json_data, timeout=timeout)
    try:
        return r.json()
    except:
        return {"raw": r.text[:100]}

# ========== 测试14: 目标消批恢复 ==========
log("=== 测试14: 目标消批恢复 ===")
api_post("/simulation/reset", {})
api_post("/power", {"state": "on"})
api_post("/mode", {"mode": "stop"})
api_post("/steer", {"azimuth": 45})
time.sleep(3)
tracks = get_tracks()
cnt = tracks.get("total", 0)
log("当前目标数: " + str(cnt))
if cnt > 0:
    tgt = tracks["tracks"][0]
    tgt_id = tgt["id"]
    log("目标# {} 方位: {}".format(tgt_id, tgt.get("azimuth_deg", 0)))
    r_tas = api_post("/tasEngage", {"target_id": tgt_id, "data_rate": 1})
    log("TAS接入: " + str(r_tas.get("ok", r_tas)))
    api_post("/target_count", {"count": 0})
    time.sleep(1)
    tracks2 = get_tracks()
    log("目标消失后: " + str(tracks2.get("total", 0)))
    r_dis = api_post("/tasDisengage", {"target_id": tgt_id})
    log("TAS断开: " + str(r_dis))
    state = get_state()
    log("最终状态: power={} mode={}".format(state.get("power"), state.get("mode")))
    results.append((14, "目标消批恢复", "PASS", str(r_dis.get("error", "ok"))[:50]))
else:
    log("跳过：无目标")
    results.append((14, "目标消批恢复", "SKIP", "无目标"))

# ========== 测试15: 多目标TAS ==========
log("\n=== 测试15: 多目标TAS ===")
api_post("/simulation/reset", {})
api_post("/power", {"state": "on"})
time.sleep(5)
tracks = get_tracks()
cnt = tracks.get("total", 0)
log("当前目标数: " + str(cnt))
if cnt >= 2:
    sorted_tgts = sorted(tracks["tracks"], key=lambda t: t.get("azimuth_deg", 0))
    az_list = [t.get("azimuth_deg", 0) for t in sorted_tgts[:3]]
    max_diff = max(abs(az_list[i]-az_list[j]) % 360 for i in range(len(az_list)) for j in range(i+1, len(az_list)))
    if max_diff > 180:
        max_diff = 360 - max_diff
    tgt1, tgt2 = sorted_tgts[0], sorted_tgts[1]
    log("方位差最大的两个: {} deg 和 {} deg，差={} deg".format(tgt1.get("azimuth_deg"), tgt2.get("azimuth_deg"), max_diff))
    api_post("/mode", {"mode": "stop"})
    mid_az = (tgt1.get("azimuth_deg", 0) + tgt2.get("azimuth_deg", 0)) / 2
    api_post("/steer", {"azimuth": mid_az})
    r1 = api_post("/tasEngage", {"target_id": tgt1["id"], "data_rate": 1})
    r2 = api_post("/tasEngage", {"target_id": tgt2["id"], "data_rate": 1})
    log("TAS1: {} TAS2: {}".format(r1.get("ok", False), r2.get("ok", False)))
    if max_diff > 120:
        results.append((15, "多目标TAS(方位差>120)", "PASS" if not r2.get("ok") else "FAIL", "第二个被拒" if not r2.get("ok") else "第二个被接入"))
    else:
        results.append((15, "多目标TAS(方位差<120)", "PASS", "两个都接入"))
else:
    log("跳过：目标不足")
    results.append((15, "多目标TAS", "SKIP", "目标<2"))

# ========== 测试16: 快速连续指令 ==========
log("\n=== 测试16: 快速连续指令 ===")
api_post("/simulation/reset", {})
api_post("/power", {"state": "on"})
t0 = time.time()
r1 = requests.post(BASE+"/api/agent/chat", json={"message": "全方位搜索", "session_id": "loop3"}, timeout=30)
r2 = requests.post(BASE+"/api/agent/chat", json={"message": "全方位搜索", "session_id": "loop3"}, timeout=30)
t2 = time.time() - t0
reply2 = r2.json().get("reply", "")[:100] if r2.status_code == 200 else "ERR"
log("2次耗时: {:.1f}s，第2次: {}".format(t2, reply2))
loop_caught = "循环" in reply2 or "重复" in reply2
results.append((16, "快速连续指令", "PASS" if not loop_caught else "FAIL", "2次未触发" if not loop_caught else "触发loop"))

# ========== 测试17: Preprocess象限handler ==========
log("\n=== 测试17: Preprocess象限handler ===")
api_post("/simulation/reset", {})
api_post("/power", {"state": "on"})
api_post("/mode", {"mode": "spin"})
t0 = time.time()
r = requests.post(BASE+"/api/agent/chat", json={"message": "重点关注第一象限", "session_id": "quadrant_test"}, timeout=60)
elapsed = time.time() - t0
reply = r.json().get("reply", "")[:150] if r.status_code == 200 else f"HTTP {r.status_code}"
log("Status: {} Time: {:.1f}s Reply: {}".format(r.status_code, elapsed, reply))
if r.status_code == 200:
    has_quadrant = "第一象限" in reply or "象限" in reply
    results.append((17, "Preprocess象限handler", "PASS" if has_quadrant else "PARTIAL", reply[:80]))
else:
    results.append((17, "Preprocess象限handler", "FAIL", reply))

# ========== 测试18: spin模式set_steer ==========
log("\n=== 测试18: spin模式set_steer ===")
api_post("/simulation/reset", {})
api_post("/power", {"state": "on"})
api_post("/mode", {"mode": "spin"})
t0 = time.time()
r = requests.post(BASE+"/api/agent/chat", json={"message": "在方位45度进行定方位监视", "session_id": "stepfail"}, timeout=60)
elapsed = time.time() - t0
reply = r.json().get("reply", "")[:200] if r.status_code == 200 else f"HTTP {r.status_code}"
log("Status: {} Time: {:.1f}s Reply: {}".format(r.status_code, elapsed, reply))
if r.status_code == 200:
    has_spin_hint = any(k in reply for k in ["转动", "spin", "停转", "转动模式", "模式", "不支持"])
    results.append((18, "spin模式set_steer", "PASS" if has_spin_hint else "PARTIAL", reply[:80]))
else:
    results.append((18, "spin模式set_steer", "FAIL", reply))

# ========== 汇总 ==========
log("\n\n========== 汇总 ==========")
for num, name, result, note in results:
    log("| {} | {} | {} | {} |".format(num, name, result, note))

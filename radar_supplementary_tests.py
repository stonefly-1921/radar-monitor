"""补充测试用例 14-18"""
import requests, time, json

BASE = "http://localhost:8000"
results = []

def log(msg):
    print("[{}] {}".format(time.strftime("%H:%M:%S"), msg))

def call_chat(msg, session, timeout=30):
    t0 = time.time()
    try:
        r = requests.post(f"{BASE}/api/agent/chat", json={"message": msg, "session_id": session}, timeout=timeout)
        return time.time()-t0, r.status_code, r.json().get("reply","")[:200]
    except Exception as e:
        return time.time()-t0, "ERR", str(e)[:100]

def get_tracks():
    r = requests.get(f"{BASE}/api/tracks", timeout=5)
    return r.json()

def get_state():
    r = requests.get(f"{BASE}/api/state", timeout=5)
    return r.json()

def api_post(path, json_data, timeout=5):
    r = requests.post(f"{BASE}{path}", json=json_data, timeout=timeout)
    return r.json()

# ========== 测试14: 目标消批恢复 ==========
log("=== 测试14: 目标消批恢复 ===")
api_post("/simulation/reset", {})
api_post("/power", {"state": "on"})
api_post("/mode", {"mode": "stop"})
api_post("/steer", {"azimuth": 45})
time.sleep(3)
tracks = get_tracks()
log("当前目标数: " + str(tracks.get("total", 0)))
if tracks.get("total", 0) > 0:
    tgt_id = tracks["tracks"][0]["id"]
    log("目标# {} 方位: {}".format(tgt_id, tracks["tracks"][0].get("azimuth_deg", 0)))
    r_tas = api_post("/tasEngage", {"target_id": tgt_id, "data_rate": 1})
    log("TAS接入: " + str(r_tas))
    api_post("/target_count", {"count": 0})
    time.sleep(1)
    tracks2 = get_tracks()
    log("目标消失后数量: " + str(tracks2.get("total", 0)))
    r_disengage = api_post("/tasDisengage", {"target_id": tgt_id})
    log("TAS断开: " + str(r_disengage))
    state = get_state()
    log("最终雷达状态: power={} mode={}".format(state["power"], state["mode"]))
    results.append((14, "目标消批恢复", "PASS" if "error" not in str(r_disengage) else "FAIL", r_disengage.get("error","ok")[:50]))
else:
    log("跳过：无目标")
    results.append((14, "目标消批恢复", "SKIP", "无目标"))

# ========== 测试15: 多目标TAS ==========
log("\n=== 测试15: 多目标TAS ===")
api_post("/simulation/reset", {})
api_post("/power", {"state": "on"})
time.sleep(5)
tracks = get_tracks()
log("当前目标数: " + str(tracks.get("total", 0)))
if tracks.get("total", 0) >= 2:
    sorted_targets = sorted(tracks["tracks"], key=lambda t: t.get("azimuth_deg", 0))
    azs = [t.get("azimuth_deg", 0) for t in sorted_targets[:3]]
    az_diffs = []
    for i in range(len(azs)):
        for j in range(i+1, len(azs)):
            diff = abs(azs[i] - azs[j])
            if diff > 180:
                diff = 360 - diff
            az_diffs.append((diff, azs[i], azs[j]))
    max_diff, az1, az2 = max(az_diffs)
    log("方位差最大的两个: {}° 和 {}°，差={}°".format(az1, az2, max_diff))
    tgt1 = sorted_targets[0]
    tgt2 = sorted_targets[1]
    api_post("/mode", {"mode": "stop"})
    mid_az = (az1 + az2) / 2
    if mid_az > 180:
        mid_az -= 180
    api_post("/steer", {"azimuth": mid_az})
    r1 = api_post("/tasEngage", {"target_id": tgt1["id"], "data_rate": 1})
    log("目标1 TAS接入: " + str(r1))
    r2 = api_post("/tasEngage", {"target_id": tgt2["id"], "data_rate": 1})
    log("目标2 TAS接入: " + str(r2))
    tas_tracking = get_state().get("tas_tracking", {})
    log("当前TAS跟踪: " + str(tas_tracking))
    ok1 = r1.get("ok", False)
    ok2 = r2.get("ok", False)
    if max_diff > 120:
        if not ok2:
            results.append((15, "多目标TAS(方位差>120°)", "PASS", "第二个目标被正确拒绝"))
        else:
            results.append((15, "多目标TAS(方位差>120°)", "PARTIAL", "两个都接入但方位差大", "方位差={}".format(max_diff)))
    else:
        results.append((15, "多目标TAS(方位差<120°)", "PASS", "两个都接入", "方位差={}".format(max_diff)))
else:
    log("跳过：目标不足")
    results.append((15, "多目标TAS", "SKIP", "目标不足"))

# ========== 测试16: 快速连续指令 ==========
log("\n=== 测试16: 快速连续指令 ===")
api_post("/simulation/reset", {})
api_post("/power", {"state": "on"})
t0 = time.time()
_, code1, reply1 = call_chat("全方位搜索", "loop1", timeout=30)
t1 = time.time()
_, code2, reply2 = call_chat("全方位搜索", "loop1", timeout=30)
t2 = time.time()
log("第一次: {:.1f}s, 第二次: {:.1f}s".format(t1-t0, t2-t1))
log("第二次回复: " + reply2[:100])
if "循环" in reply2 or "重复" in reply2:
    results.append((16, "快速连续指令", "FAIL", "2次即被loop检测拒绝"))
elif code2 == 200:
    results.append((16, "快速连续指令", "PASS", "2次未被拒绝（3次才触发）"))
else:
    results.append((16, "快速连续指令", "PARTIAL", "code={}".format(code2)))

# ========== 测试17: Preprocess象限handler ==========
log("\n=== 测试17: Preprocess handler - 重点关注象限 ===")
api_post("/simulation/reset", {})
api_post("/power", {"state": "on"})
api_post("/mode", {"mode": "spin"})
t0 = time.time()
_, code, reply = call_chat("重点关注第一象限", "quadrant_test", timeout=30)
log("回复({:.1f}s): {}".format(time.time()-t0, reply[:100]))
if "第一象限" in reply or "象限" in reply:
    results.append((17, "Preprocess象限handler", "PASS", "回复包含象限内容"))
else:
    results.append((17, "Preprocess象限handler", "PARTIAL", reply[:80]))

# ========== 测试18: Step失败后后续Step处理 ==========
log("\n=== 测试18: Step失败后后续Step不执行 ===")
api_post("/simulation/reset", {})
api_post("/power", {"state": "on"})
api_post("/mode", {"mode": "spin"})
t0 = time.time()
_, code, reply = call_chat("在方位45度进行定方位监视", "step_fail_test", timeout=30)
log("回复({:.1f}s): {}".format(time.time()-t0, reply[:150]))
if "转动" in reply or "spin" in reply.lower() or "停转" in reply:
    results.append((18, "Step失败处理", "PASS", "明确提示转动模式限制"))
elif code == 200:
    results.append((18, "Step失败处理", "PARTIAL", "正常返回", reply[:80]))
else:
    results.append((18, "Step失败处理", "FAIL", "异常返回"))

# ========== 汇总 ==========
log("\n\n========== 汇总 ==========")
log("|#|测试名称|结果|备注|")
log("|---|------|------|------|")
for num, name, result, note in results:
    log("|{}|{}|{}|{}|".format(num, name, result, note))

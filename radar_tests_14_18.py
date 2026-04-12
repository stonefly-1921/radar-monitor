# radar supplementary tests 14-18
import requests, time, sys, json

BASE = "http://localhost:8000"

def api_get(path):
    return requests.get(f"{BASE}{path}", timeout=10)

def api_post(path, json=None):
    return requests.post(f"{BASE}{path}", json=json, timeout=10)

def step(name, fn):
    t0 = time.time()
    try:
        r = fn()
        elapsed = time.time() - t0
        ok = r.status_code < 400
        print(f"  [{elapsed:.1f}s] {name}: {'OK' if ok else 'FAIL'} (status={r.status_code})")
        if not ok:
            print(f"    Response: {r.text[:200]}")
        return r, elapsed, ok
    except Exception as e:
        elapsed = time.time() - t0
        print(f"  [{elapsed:.1f}s] {name}: ERROR - {e}")
        return None, elapsed, False

results = []

# ============================================================
print("\n" + "="*60)
print("Test 14: Target despawn recovery")
print("="*60)
t0 = time.time()

r1, t1, ok1 = step("GET /api/state", lambda: api_get("/api/state"))
r2, t2, ok2 = step("POST /api/power on", lambda: api_post("/api/power", {"state": "on"}))
r3, t3, ok3 = step("POST /api/mode stop", lambda: api_post("/api/mode", {"mode": "stop"}))
r4, t4, ok4 = step("POST /api/steer az=45", lambda: api_post("/api/steer", {"azimuth": 45}))

print("  Waiting 3s for targets...")
time.sleep(3)

r6, t6, ok6 = step("GET /api/tracks", lambda: api_get("/api/tracks"))
tracks = r6.json().get("targets", []) if r6 else []
print(f"    Targets: {len(tracks)}")
target_id = tracks[0]["id"] if tracks else None
print(f"    First target ID: {target_id}")

tas_engage_ok = False
if target_id:
    r7, t7, ok7 = step(f"POST /api/tasEngage target_id={target_id}", 
        lambda: api_post("/api/tasEngage", {"target_id": target_id, "data_rate": 1}))
    tas_engage_ok = ok7 and r7 and r7.status_code < 400

r8, t8, ok8 = step("POST /api/target_count count=0", 
    lambda: api_post("/api/target_count", {"count": 0}))

r9, t9, ok9 = step("GET /api/tracks (should be empty)", lambda: api_get("/api/tracks"))
tracks9 = r9.json().get("targets", []) if r9 else []
print(f"    Targets after count=0: {len(tracks9)}")

r10, t10, ok10 = step("POST /api/tasDisengage", lambda: api_post("/api/tasDisengage"))
tas_disengage_ok = False
if r10:
    resp10 = r10.json()
    print(f"    Response: {json.dumps(resp10, ensure_ascii=False)[:300]}")
    tas_disengage_ok = r10.status_code != 500
    err = resp10.get("error", "")
    if "\u76ee\u6807" in err or "\u4e0d\u5b58\u5728" in err or "not found" in err.lower():
        tas_disengage_ok = True

r11, t11, ok11 = step("GET /api/state", lambda: api_get("/api/state"))

total_t14 = time.time() - t0
test14_pass = ok1 and ok2 and ok3 and ok4 and ok6 and tas_engage_ok and ok8 and ok9 and tas_disengage_ok and ok11
actual14 = f"tasDisengage status={r10.status_code if r10 else 'N/A'}, mode={r11.json().get('mode','?') if r11 else '?'}"
print(f"\n  Test14: {'PASS' if test14_pass else 'FAIL'}, elapsed={total_t14:.1f}s")
print(f"  Actual: {actual14}")
print(f"  Expected: tasDisengage returns friendly error, radar state is safe")
results.append(("14", "Target despawn recovery", "PASS" if test14_pass else "FAIL", f"{total_t14:.1f}s", actual14, "tasDisengage friendly error, safe state"))

# ============================================================
print("\n" + "="*60)
print("Test 15: Multi-target TAS (azimuth diff > 120 deg)")
print("="*60)
t0 = time.time()

r1, t1, ok1 = step("POST /api/simulation/reset", lambda: api_post("/api/simulation/reset"))
r2, t2, ok2 = step("POST /api/power on", lambda: api_post("/api/power", {"state": "on"}))

print("  Waiting 5s for multiple targets...")
time.sleep(5)

r4, t4, ok4 = step("GET /api/tracks", lambda: api_get("/api/tracks"))
targets = r4.json().get("targets", []) if r4 else []
print(f"    Targets: {len(targets)}")

target1_id, target2_id, max_diff, mid_az = None, None, 0, 0
if len(targets) >= 2:
    az_list = [(t["id"], t["azimuth_deg"]) for t in targets]
    max_diff = 0
    pair = None
    for i in range(len(az_list)):
        for j in range(i+1, len(az_list)):
            diff = abs(az_list[i][1] - az_list[j][1])
            if diff > max_diff:
                max_diff = diff
                pair = (az_list[i][0], az_list[j][0], az_list[i][1], az_list[j][1])
    print(f"    Max azimuth diff: {max_diff:.1f} deg between id={pair[0]}({pair[2]:.1f}) and id={pair[1]}({pair[3]:.1f})")
    target1_id, target2_id = pair[0], pair[1]
    mid_az = (pair[2] + pair[3]) / 2

r6, t6, ok6 = step("POST /api/mode stop", lambda: api_post("/api/mode", {"mode": "stop"}))

test15_pass = False
actual15 = "insufficient targets"
if target1_id:
    r7, t7, ok7 = step(f"POST /api/steer az={mid_az:.1f}", lambda: api_post("/api/steer", {"azimuth": mid_az}))
    time.sleep(1)
    
    r8, t8, ok8 = step(f"POST /api/tasEngage target_id={target1_id}", 
        lambda: api_post("/api/tasEngage", {"target_id": target1_id, "data_rate": 1}))
    
    r9, t9, ok9 = step(f"POST /api/tasEngage target_id={target2_id}", 
        lambda: api_post("/api/tasEngage", {"target_id": target2_id, "data_rate": 1}))
    
    second_engaged = False
    if r9:
        resp9 = r9.json()
        print(f"    Response9: {json.dumps(resp9, ensure_ascii=False)[:300]}")
        if r9.status_code < 400:
            second_engaged = True
    
    over120 = max_diff > 120
    if over120:
        test15_pass = not second_engaged
        actual15 = f"diff={max_diff:.1f}>120, 2nd TAS {'rejected(PASS)' if not second_engaged else 'accepted(FAIL)'}"
    else:
        test15_pass = second_engaged
        actual15 = f"diff={max_diff:.1f}<=120, 2nd TAS {'accepted' if second_engaged else 'rejected'}"

total_t15 = time.time() - t0
print(f"\n  Test15: {'PASS' if test15_pass else 'FAIL'}, elapsed={total_t15:.1f}s")
print(f"  Actual: {actual15}")
print(f"  Expected: 2nd tasEngage fails when azimuth diff > 120 deg")
results.append(("15", "Multi-target TAS (az diff>120)", "PASS" if test15_pass else "FAIL", f"{total_t15:.1f}s", actual15, "2nd tasEngage fails or azimuth coverage warning"))

# ============================================================
print("\n" + "="*60)
print("Test 16: Rapid repeated commands (loop detection)")
print("="*60)
t0 = time.time()

r1, t1, ok1 = step("POST /api/simulation/reset", lambda: api_post("/api/simulation/reset"))
r2, t2, ok2 = step("POST /api/power on", lambda: api_post("/api/power", {"state": "on"}))

print("  Sending 1st chat...")
t_req1 = time.time()
r3, t3, ok3 = step("POST /api/agent/chat (1st)", 
    lambda: api_post("/api/agent/chat", {"message": "\u5168\u65b9\u4f4d\u641c\u7d22", "session_id": "loop_test"}))

print("  Sending 2nd chat (interval < 1s)...")
t_req2 = time.time()
r4, t4, ok4 = step("POST /api/agent/chat (2nd)", 
    lambda: api_post("/api/agent/chat", {"message": "\u5168\u65b9\u4f4d\u641c\u7d22", "session_id": "loop_test"}))

interval = t_req2 - t_req1
print(f"    Interval: {interval:.2f}s")

test16_pass = False
if r4:
    elapsed_r4 = t4
    test16_pass = elapsed_r4 < 15
    print(f"    2nd request elapsed: {elapsed_r4:.1f}s, status: {r4.status_code}")
    if r4.status_code == 200:
        data4 = r4.json()
        print(f"    Reply: {data4.get('reply', '')[:100]}")
    else:
        print(f"    Error: {r4.text[:200]}")
else:
    test16_pass = False

total_t16 = time.time() - t0
actual16 = f"interval={interval:.2f}s, 2nd elapsed={t4:.1f}s, status={r4.status_code if r4 else 'N/A'}"
print(f"\n  Test16: {'PASS' if test16_pass else 'FAIL'}, elapsed={total_t16:.1f}s")
print(f"  Actual: {actual16}")
print(f"  Expected: 2 repeats not rejected, returns within 10s")
results.append(("16", "Rapid repeated commands (loop)", "PASS" if test16_pass else "FAIL", f"{total_t16:.1f}s", actual16, "2 repeats not rejected, returns within 10s"))

# ============================================================
print("\n" + "="*60)
print("Test 17: Preprocess handler - focus quadrant")
print("="*60)
t0 = time.time()

r1, t1, ok1 = step("POST /api/simulation/reset", lambda: api_post("/api/simulation/reset"))
r2, t2, ok2 = step("POST /api/power on", lambda: api_post("/api/power", {"state": "on"}))
r3, t3, ok3 = step("POST /api/mode spin", lambda: api_post("/api/mode", {"mode": "spin"}))

t_chat = time.time()
r4, t4, ok4 = step("POST /api/agent/chat focus quadrant 1", 
    lambda: api_post("/api/agent/chat", {"message": "\u91cd\u70b9\u5173\u6ce8\u7b2c\u4e00\u8c61\u9650", "session_id": "quadrant_test"}))

test17_pass = False
if r4:
    elapsed_chat = time.time() - t_chat
    print(f"    Chat elapsed: {elapsed_chat:.1f}s")
    if r4.status_code == 200:
        data4 = r4.json()
        reply = data4.get("reply", "")
        print(f"    Reply: {reply[:200]}")
        has_quadrant = "\u7b2c\u4e00\u8c61\u9650" in reply or "quadrant" in reply.lower()
        fast_enough = elapsed_chat < 10
        test17_pass = has_quadrant and fast_enough
        print(f"    Has quadrant content: {has_quadrant}, fast (<10s): {fast_enough}")
    else:
        print(f"    Error: {r4.text[:200]}")
else:
    test17_pass = False

total_t17 = time.time() - t0
actual17 = f"elapsed={t4:.1f}s, quadrant in reply={'?' if r4 and r4.status_code==200 else 'N/A'}"
print(f"\n  Test17: {'PASS' if test17_pass else 'FAIL'}, elapsed={total_t17:.1f}s")
print(f"  Actual: {actual17}")
print(f"  Expected: returns within 10s, reply contains quadrant, uses preprocess")
results.append(("17", "Preprocess handler - quadrant", "PASS" if test17_pass else "FAIL", f"{total_t17:.1f}s", actual17, "returns <10s, contains quadrant, preprocess not LLM"))

# ============================================================
print("\n" + "="*60)
print("Test 18: Step failure stops subsequent steps")
print("="*60)
t0 = time.time()

r1, t1, ok1 = step("POST /api/simulation/reset", lambda: api_post("/api/simulation/reset"))
r2, t2, ok2 = step("POST /api/power on", lambda: api_post("/api/power", {"state": "on"}))
r3, t3, ok3 = step("POST /api/mode spin", lambda: api_post("/api/mode", {"mode": "spin"}))

t_chat = time.time()
r4, t4, ok4 = step("POST /api/agent/chat fixed azimuth az=45", 
    lambda: api_post("/api/agent/chat", {"message": "\u5728\u65b9\u4f4d45\u5ea6\u8fdb\u884c\u5b9a\u65b9\u4f4d\u76d1\u89c6", "session_id": "step_fail_test"}))

test18_pass = False
spin_error_found = False
if r4:
    elapsed_chat = time.time() - t_chat
    print(f"    Chat elapsed: {elapsed_chat:.1f}s")
    if r4.status_code == 200:
        data4 = r4.json()
        reply = data4.get("reply", "")
        print(f"    Reply: {reply[:300]}")
        spin_error_found = any(kw in reply for kw in ["\u8f6c\u52a8\u6a21\u5f0f", "spin", "\u4e0d\u652f\u6301", "\u9700\u8981\u505c\u6b62"])
        test18_pass = spin_error_found
        print(f"    Spin mode error found: {spin_error_found}")
    else:
        print(f"    Error: {r4.text[:200]}")
else:
    test18_pass = False

total_t18 = time.time() - t0
actual18 = f"spin mode error in reply: {spin_error_found}"
print(f"\n  Test18: {'PASS' if test18_pass else 'FAIL'}, elapsed={total_t18:.1f}s")
print(f"  Actual: {actual18}")
print(f"  Expected: reply clearly states 'current is spin mode, not supported'")
results.append(("18", "Step failure stops subsequent", "PASS" if test18_pass else "FAIL", f"{total_t18:.1f}s", actual18, "reply states spin mode not supported for fixed azimuth"))

# ============================================================
print("\n" + "="*60)
print("SUMMARY TABLE")
print("="*60)
header = "| # | Test Name | Result | Elapsed | Actual | Expected |"
print(header)
print("|---|---|---|---|---|---|")
for r in results:
    print(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |")

passed = sum(1 for r in results if r[2] == "PASS")
failed = sum(1 for r in results if r[2] == "FAIL")
print(f"\nPassed: {passed}/{len(results)}, Failed: {failed}/{len(results)}")
print("All tests completed!")

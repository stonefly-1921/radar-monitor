"""Ollama + qwen3:4b 测试关键用例"""
import requests, time, sys

BASE = "http://localhost:8000"

def log(msg):
    sys.stdout.write("[{}] {}\n".format(time.strftime("%H:%M:%S"), msg))
    sys.stdout.flush()

def test(name, msg, session, timeout=60):
    requests.post(BASE+"/api/simulation/reset", json={}, timeout=5)
    requests.post(BASE+"/api/power", json={"state": "on"}, timeout=5)
    t0 = time.time()
    r = requests.post(BASE+"/api/agent/chat", json={"message": msg, "session_id": session}, timeout=timeout)
    elapsed = time.time() - t0
    reply = r.json().get("reply", "")[:120] if r.status_code == 200 else f"HTTP {r.status_code}"
    status = "PASS" if r.status_code == 200 else "FAIL"
    log(f"[{status}] {name} | {elapsed:5.1f}s | {reply}")
    return r.status_code == 200, elapsed, reply

log("=== Ollama qwen3:4b-instruct 测试 ===\n")

# Test 16: 快速连续
test("Test16-快速连续(2次)", "全方位搜索", "ollama_t16")

# Test 17: 重点关注象限
test("Test17-重点关注第一象限", "重点关注第一象限", "ollama_t17")

# Test 18: spin模式定方位
requests.post(BASE+"/api/mode", json={"mode": "spin"}, timeout=5)
test("Test18-spin模式定方位", "在方位45度进行定方位监视", "ollama_t18")

# 基本指令测试
log("")
test("开机+模式切换", "全方位搜索", "ollama_basic")
test("目标识别", "目标识别", "ollama_identify")
test("TAS接入(stop模式)", "停转模式", "ollama_stop")

log("\n=== 测试完成 ===")

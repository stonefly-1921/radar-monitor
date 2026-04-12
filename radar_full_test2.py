import subprocess
import requests
import json
import time
import sys

BASE = "http://localhost:8000"

# Start server as subprocess
print("启动后端服务器...")
server_proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"],
    cwd=r"E:\radar-brain-github\backend",
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
time.sleep(5)

# Verify server up
try:
    r = requests.get(f"{BASE}/api/state", timeout=5)
    print(f"服务器就绪: {r.json()['power']}")
except Exception as e:
    print(f"服务器启动失败: {e}")
    print(server_proc.stdout.readline().decode(errors="replace"))
    sys.exit(1)

def chat(msg, session="test"):
    r = requests.post(f"{BASE}/api/agent/chat", json={"message": msg, "session_id": session}, timeout=120)
    try:
        return r.json()
    except:
        return {"error": r.text}

def state():
    r = requests.get(f"{BASE}/api/state", timeout=5)
    return r.json()

def get_reply(r):
    if isinstance(r, dict) and "reply" in r:
        return r["reply"]
    if isinstance(r, dict) and "response" in r:
        return r["response"]
    return str(r)

def target_summary(s):
    detected = [t for t in s['targets'] if t.get('detected')]
    tracked = [t for t in s['targets'] if t.get('tracked')]
    tas = [t for t in s['targets'] if t.get('tas_mode')]
    return f"检测{detected.__len__()}批 / 起批{tracked.__len__()}批 / TAS{tas.__len__()}批"

print("=" * 65)
print("组别一：基础功能测试")
print("=" * 65)

# 重置
requests.post(f"{BASE}/api/simulation/reset", timeout=5)

# Test 1
print("\n[1] 开机并全方位搜索")
r1 = chat("开机并全方位搜索")
reply1 = get_reply(r1)
print(f"  回复: {reply1[:200]}")
time.sleep(5)
s1 = state()
print(f"  状态: power={s1['power']}, mode={s1['mode']}, {target_summary(s1)}")

# Test 2
print("\n[2] 目前起批几个目标？")
r2 = chat("目前起批几个目标？")
reply2 = get_reply(r2)
print(f"  回复: {reply2[:200]}")
s2 = state()
print(f"  状态: {target_summary(s2)}")

time.sleep(8)
s2b = state()
print(f"  等待后: {target_summary(s2b)}")
for t in s2b['targets']:
    if t.get('detected') or t.get('tracked'):
        print(f"    #{t['id']} {t['model']} az={t['azimuth_deg']:.0f} dist={t['distance_m']/1000:.0f}km tracked={t.get('tracked')}")

# Test 3 - TAS在转动模式下应拒绝
print("\n[3] 对某批目标进行TAS跟踪（转动模式应拒绝）")
r3 = chat("对1号目标进行跟踪")
reply3 = get_reply(r3)
print(f"  回复: {reply3[:250]}")

# Test 4 - 停转后TAS
print("\n[4] 停转后对1号目标TAS跟踪")
r4 = chat("先停转，然后对1号目标进行跟踪")
reply4 = get_reply(r4)
print(f"  回复: {reply4[:250]}")
time.sleep(2)
s4 = state()
tas4 = s4.get('tas_tracking', {})
print(f"  TAS状态: {tas4}")
print(f"  天线角度: {s4['antenna_angle_deg']:.1f}度  steer={s4.get('steer_azimuth_deg', 0):.1f}度")

# Test 5 - 数据率调整
print("\n[5] 把1号目标跟踪数据率改为10Hz")
r5 = chat("把1号目标的跟踪数据率改成10赫兹")
reply5 = get_reply(r5)
print(f"  回复: {reply5[:200]}")
time.sleep(1)
s5 = state()
tas5 = s5.get('tas_tracking', {})
print(f"  TAS状态: {tas5}")

# Test 6 - 识别
print("\n[6] 对1号目标进行识别")
r6 = chat("对1号目标进行识别")
reply6 = get_reply(r6)
print(f"  回复: {reply6[:200]}")
time.sleep(3)
s6 = state()
t1s6 = next((t for t in s6['targets'] if t['id']==1), None)
if t1s6:
    print(f"  1号目标identified_model: {t1s6.get('identified_model')}")

# Test 7
print("\n[7] 当前有哪些类型的已识别目标")
r7 = chat("当前有哪些类型的已识别目标？")
reply7 = get_reply(r7)
print(f"  回复: {reply7[:200]}")

print("\n" + "=" * 65)
print("组别二：组合高等级测试")
print("=" * 65)

requests.post(f"{BASE}/api/simulation/reset", timeout=5)
requests.post(f"{BASE}/api/power", json={"state": "on"}, timeout=5)
requests.post(f"{BASE}/api/mode", json={"mode": "spin"}, timeout=5)
print("已重置+开机，等待目标起批...")
time.sleep(12)

# Test 8
print("\n[8] 对所有目标识别（转动→应先停转）")
r8 = chat("请对所有目标进行识别，并上报识别结果")
reply8 = get_reply(r8)
print(f"  回复: {reply8[:300]}")
time.sleep(5)
s8 = state()
tas8 = s8.get('tas_tracking', {})
identified = [(t['id'], t.get('identified_model') or t.get('model')) for t in s8['targets'] if t.get('identified_model')]
print(f"  识别结果: {identified}")
print(f"  TAS状态: {tas8}")

# Test 9
print("\n[9] 对1、2、3号目标TAS（应建议停转角度）")
r9 = chat("请对1号、2号、3号目标转TAS跟踪")
reply9 = get_reply(r9)
print(f"  回复: {reply9[:300]}")
time.sleep(3)
s9 = state()
tas9 = s9.get('tas_tracking', {})
print(f"  TAS状态: {tas9}")
print(f"  steer角度: {s9.get('steer_azimuth_deg', 0):.1f}度")

# Test 10
print("\n[10] 对F22目标TAS")
r10 = chat("请对F22这样的目标进行TAS跟踪")
reply10 = get_reply(r10)
print(f"  回复: {reply10[:300]}")
time.sleep(2)
s10 = state()
tas10 = s10.get('tas_tracking', {})
print(f"  TAS状态: {tas10}")

# Test 11
print("\n[11] 对第一象限目标转跟踪")
r11 = chat("请对第一象限的目标转跟踪")
reply11 = get_reply(r11)
print(f"  回复: {reply11[:300]}")
time.sleep(2)
s11 = state()
tas11 = s11.get('tas_tracking', {})
first_q = [t for t in s11['targets'] if 0 <= t.get('azimuth_deg',0) < 90]
print(f"  第一象限目标: {[(t['id'], t['model']) for t in first_q]}")
print(f"  TAS状态: {tas11}")

# Test 12
print("\n[12] 跟踪了哪些目标？数据率？")
r12 = chat("当前跟踪了哪些目标？每个目标的数据率是多少？")
reply12 = get_reply(r12)
print(f"  回复: {reply12[:300]}")

print("\n" + "=" * 65)
print("测试完成，关闭服务器")
print("=" * 65)
server_proc.terminate()
server_proc.wait(timeout=5)

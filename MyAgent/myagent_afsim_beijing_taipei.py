"""
MyAgent 北京→台北弹道导弹仿真任务
完整测试：从 AFSIM 源码分析 → 弹道计算 → 输出结果
"""
import sys, os, json
sys.path.insert(0, r'C:\Users\15041\.openclaw\workspace\MyAgent')

from agent import loop_v2

USER_TASK = """请完成以下任务：

1. 读取 AFSIM 源码目录 D:\afsim-2.9.0-win64\swdev\src\wsf_plugins\wsf_fires\source\
   找出弹道导弹仿真相关的关键源文件

2. 读取 FiresPath.cpp，理解弹道计算公式（重点：一阶阻力模型 exp(-dt/tc)）

3. 用 Python 实现从北京(39.9°N, 116.4°E)到台北(25.0°N, 121.5°E)的弹道计算
   使用 AFSIM FiresPath 相同的一阶阻力模型，计算：
   - 射程（约 1724 km 大圆距离）
   - 射角、初速、飞行时间、最大弹道高

4. 输出仿真结果
"""

# 模拟 LLM 的多轮回复
LLM_RESPONSES = [
    # Round 1: file_list 列出源码
    json.dumps({
        "think": "用户要分析 AFSIM 弹道导弹仿真并计算北京到台北的弹道。我先列出源码目录。",
        "action": "tool_call",
        "tools": [{"tool": "file_list", "params": {"path": "D:\\afsim-2.9.0-win64\\swdev\\src\\wsf_plugins\\wsf_fires\\source"}}]
    }),
    # Round 2: file_read FiresPath.cpp（核心弹道计算）
    json.dumps({
        "think": "关键文件是 FiresPath.cpp，包含一阶阻力模型。让我读它理解弹道计算公式。",
        "action": "tool_call",
        "tools": [{"tool": "file_read", "params": {"path": "D:\\afsim-2.9.0-win64\\swdev\\src\\wsf_plugins\\wsf_fires\\source\\FiresPath.cpp"}}]
    }),
    # Round 3: 用 Python 计算弹道
    json.dumps({
        "think": "已理解 FiresPath 的弹道模型。现在用 Python 实现北京→台北弹道计算，使用相同的一阶阻力模型。",
        "action": "tool_call",
        "tools": [{
            "tool": "python_run",
            "params": {
                "script": """
import math

g = 9.81  # m/s^2

# Haversine 大圆距离
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2-lat1)
    dlam = math.radians(lon2-lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2*R*math.asin(math.sqrt(a))

R = haversine(39.9, 116.4, 25.0, 121.5) * 1000  # 米
print(f"射程: {R/1000:.1f} km")

# FiresPath 一阶阻力模型
# vx = v0x*exp(-dt/tc), vz = v0z*exp(-dt/tc) - tc*g*(1-exp(-dt/tc))
# x = tc*v0x*(1-exp(-dt/tc))
# z = -tc*g*dt + tc*(v0z+tc*g)*(1-exp(-dt/tc)) = 0 (落地)

# 数值求解：给定 tc=300s, elev=45deg，求 dt 和 v0
tc = 300.0
elev = math.radians(45.0)
for dt in range(100, 1200):
    t1 = 1.0 - math.exp(-dt/tc)
    v0x = R / (tc*t1)
    v0z = v0x * math.tan(elev)
    z = -tc*g*dt + tc*(v0z+tc*g)*t1
    if z <= 0:
        v0 = v0x / math.cos(elev)
        # 求最大高度
        for tm in range(1, dt):
            t2 = math.exp(-tm/tc)
            t3 = 1.0-t2
            vz = v0z*t2 - tc*g*t3
            if vz <= 0:
                h = max(0, -tc*g*tm + tc*(v0z+tc*g)*t3)
                break
        print(f"tc={tc}s, 射角=45deg")
        print(f"落地时间: {dt}s ({dt/60:.2f} min)")
        print(f"初速 v0: {v0:.1f} m/s = {v0/1000:.3f} km/s ({v0/343:.1f} 马赫)")
        print(f"最大弹道高: {h/1000:.1f} km")
        break
"""
            }
        }]
    }),
    # Round 4: 输出最终答案
    json.dumps({
        "think": "弹道计算完成，得到了具体数值。现在给出完整总结。",
        "action": "final",
        "answer": """北京→台北弹道导弹 AFSIM FiresPath 仿真结果：

射程：1724 km（大圆弧）
弹道模型：AFSIM FiresPath 一阶阻力模型

参数：tc=300s, 射角=45°
- 落地时间：约 870 秒（约 14.5 分钟）
- 初速：约 8600 m/s（约 25 马赫）
- 最大弹道高：约 835 km（进入亚轨道）

公式依据（FiresPath.cpp UpdateState）：
  vx = v0x * exp(-dt/tc)
  vz = v0z * exp(-dt/tc) - tc*g*(1-exp(-dt/tc))
  x  = tc*v0x*(1-exp(-dt/tc))
  z  = -tc*g*dt + tc*(v0z+tc*g)*(1-exp(-dt/tc))

结论：弹道计算在 Python 侧完成（与 kill-chain-sim 架构一致），
AFSIM 本身通过 DIS Fire PDU 接收发射指令并进行交战评估。"""
    }),
]

resp_idx = [0]
tool_call_total = [0]

# Patch skip write
loop_v2.AgentLoopV2._save_prompt = lambda self, p: None

# Patch wait_for_response - inject LLM replies
original_wait = loop_v2.AgentLoopV2._wait_for_response
def counting_wait(self):
    resp = LLM_RESPONSES[resp_idx[0]] if resp_idx[0] < len(LLM_RESPONSES) else json.dumps({"action": "final", "answer": "完成"})
    resp_idx[0] += 1
    print(f"\n[Round {resp_idx[0]}] LLM 回复已注入")
    return resp
loop_v2.AgentLoopV2._wait_for_response = counting_wait

# Patch execute_tools_display - count calls
original_exec = loop_v2.AgentLoopV2._execute_tools_display
def counting_exec(self, tcs):
    r = original_exec(self, tcs)
    for tc in tcs:
        tool_call_total[0] += 1
        tool = tc.get('tool', '?')
        params = tc.get('params', {})
        path = params.get('path', params.get('params', {}).get('path', '') if isinstance(params.get('params'), dict) else str(params))
        print(f"  工具#{tool_call_total[0]}: {tool} → {path[:60]}")
    return r
loop_v2.AgentLoopV2._execute_tools_display = counting_exec

# Cleanup io
io_dir = r'C:\Users\15041\.openclaw\workspace\MyAgent\captured_io'
os.makedirs(io_dir, exist_ok=True)
for f in ['input.txt', 'prompt.txt', 'response.txt', 'tool_result.json']:
    p = os.path.join(io_dir, f)
    if os.path.exists(p):
        os.remove(p)

loop = loop_v2.AgentLoopV2()
loop._testing_mode = True
loop._testing_input_queue = [USER_TASK]
loop.io_dir = io_dir

print("=" * 60)
print("MyAgent 北京→台北弹道导弹仿真")
print("=" * 60)
result = loop.rewrite_main_loop()
print()
print("=" * 60)
print(f"LLM 调用：{resp_idx[0]} 次")
print(f"工具调用：{tool_call_total[0]} 次")
print(f"最终答案：\n{result.get('content','N/A')}")
print("=" * 60)

# Restore
loop_v2.AgentLoopV2._save_prompt = original_wait.__self__._save_prompt if hasattr(original_wait, '__self__') else lambda self, p: None
loop_v2.AgentLoopV2._wait_for_response = original_wait
loop_v2.AgentLoopV2._execute_tools_display = original_exec
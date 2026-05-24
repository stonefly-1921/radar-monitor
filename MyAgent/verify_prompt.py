"""验证当前优化后的 prompt 内容"""
import sys, os, tempfile, shutil, json
sys.path.insert(0, r'C:\Users\15041\.openclaw\workspace\MyAgent')
from agent.loop_v2 import AgentLoopV2

base = tempfile.mkdtemp()
io_dir = os.path.join(base, "io")
os.makedirs(io_dir, exist_ok=True)
loop = AgentLoopV2()
loop.base_dir = base
loop._testing_mode = True
loop._testing_input_queue = []
loop._testing_response_queue = []
loop.initialize()

# Simulate turn=3 with task state + tool results
loop._task_state = {
    "goal": "分析 AFSIM 弹道导弹仿真",
    "turn": 3,
    "steps_taken": [
        {"tool": "file_list", "finding": "列出源码目录，找到4个关键文件"},
        {"tool": "file_read", "finding": "FiresPath.cpp 包含一阶阻力模型 exp(-dt/tc)"},
    ],
    "pending": "还需要读 FiresMover.cpp",
    "errors": [],
}

prompt = loop.build_prompt_text(
    user_input="分析 AFSIM 弹道导弹仿真原理",
    turn=3,
    tool_results=[{
        "tool": "file_read",
        "params": {"path": "FiresPath.cpp"},
        "result": {
            "success": True,
            "result": "// Ballistic missile trajectory model\nvx = v0x * exp(-dt/tc);\nvz = v0z * exp(-dt/tc) - tc*g*(1-exp(-dt/tc));\n// KEY: 阻力衰减公式"
        }
    }],
    conversation=[]
)

print("=" * 60)
print("优化后的 prompt 内容（turn=3，工具执行后）")
print("=" * 60)
print(prompt[:3000])
print()
print("..." + prompt[-500:])
print()
print("=" * 60)
print(f"总长度: {len(prompt)} 字符")
print(f"含【本轮状态】: {'【本轮状态】' in prompt}")
print(f"含【工具执行结果分析】: {'【工具执行结果分析】' in prompt}")
print(f"含 exp(-dt/tc): {'exp(-dt/tc)' in prompt}")
print("=" * 60)

shutil.rmtree(base, ignore_errors=True)
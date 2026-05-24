"""Verify prompt optimization - check build_prompt_text behavior"""
import sys, os
sys.path.insert(0, r'C:\Users\15041\.openclaw\workspace\MyAgent')

from agent.loop_v2 import AgentLoopV2
import tempfile, shutil

base = tempfile.mkdtemp()
os.makedirs(os.path.join(base, "io"), exist_ok=True)

try:
    loop = AgentLoopV2()
    loop.base_dir = base
    loop._testing_mode = True
    loop._testing_input_queue = []
    loop._testing_response_queue = []
    loop.initialize()

    # Test 1: 25-entry conversation truncation
    print("Test 1: 25-entry conversation truncation")
    long_conv = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"t{i}"} for i in range(25)]
    prompt = loop.build_prompt_text("task", turn=15, tool_results=[], conversation=long_conv)

    # Count history lines - should be < 25 if truncated
    user_lines = prompt.count("[user]:")
    asst_lines = prompt.count("[assistant]:")
    total_lines = user_lines + asst_lines

    # Check for truncation marker or early summary
    has_truncation = ("..." in prompt) or (total_lines < 25)
    print(f"  Total history lines in prompt: {total_lines} (should be < 25)")
    print(f"  Has truncation: {has_truncation}")

    # Test 2: Check memory compression actually works
    print("\nTest 2: Memory real compression")
    from memory.core import Memory
    mem = Memory(config={"max_tokens": 100})
    for i in range(20):
        mem.add_turn("user", f"turn {i}")
    mem._auto_summarize()
    print(f"  summaries created: {len(mem.data['summaries'])} (should be >= 1)")
    print(f"  short_term reduced: {len(mem.data['short_term'])} (should be < 20)")
    print(f"  compression PASS: {len(mem.data['summaries']) > 0}")

    print("\nAll verifications complete")

finally:
    shutil.rmtree(base, ignore_errors=True)
"""
MyAgent E2E 测试 - CLI驱动完整多轮循环
======================================
使用 cli.py --exec 完整多轮循环，通过 io/ 目录文件与真实 LLM 交互。
不依赖 GUI，不修改实现代码。

测试流程:
  测试写 input.txt → cli.py --exec (bg) 生成 prompt.txt
  → 测试读 prompt.txt → 调用真实 LLM → 写 response.txt
  → cli.py 执行工具 → 生成下一轮 prompt.txt → ...
  → 直到 final_answer.txt

用法:
  python tests/test_e2e_cli.py
  pytest tests/test_e2e_cli.py -v -s
"""
import os
import sys
import json
import subprocess
import time
import threading
import unittest

MYAGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IO_DIR = os.path.join(MYAGENT_DIR, "io")
os.makedirs(IO_DIR, exist_ok=True)

sys.path.insert(0, MYAGENT_DIR)

# API配置（与 cli.py 一致）
API_KEY = subprocess.run(
    ["powershell", "-Command", "[Environment]::GetEnvironmentVariable('MINIMAX_API_KEY', 'User')"],
    capture_output=True, text=True, encoding="utf-8"
).stdout.strip()

LLM_ENDPOINT = "https://api.minimaxi.com/anthropic/v1/messages"
LLM_MODEL = "MiniMax-M2.7"


def call_llm(prompt_text: str) -> dict:
    """直接调用 LLM API，返回 parsed JSON"""
    import urllib.request

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt_text}],
        "max_tokens": 8192,
        "temperature": 0.7
    }
    req = urllib.request.Request(
        LLM_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        for item in result.get("content", []):
            if item.get("type") == "text":
                text = item.get("text", "").strip()
                if text:
                    try:
                        return json.loads(text)
                    except:
                        return {"action": "final", "answer": text}
    return None


def clean_io_files():
    for f in ["input.txt", "prompt.txt", "response.txt", "final_answer.txt", "tool_result.json"]:
        p = os.path.join(IO_DIR, f)
        if os.path.exists(p):
            open(p, "w", encoding="utf-8").write("")


def run_full_e2e(task: str, timeout: int = 300) -> dict:
    """
    完整 E2E 测试流程：
    1. 清空 io/
    2. 写任务到 input.txt
    3. 后台启动 cli.py --exec
    4. 轮询 prompt.txt → LLM → response.txt 循环
    5. 等待 final_answer.txt 或超时
    返回: {"success": bool, "turns": N, "final_answer": str, "tool_calls": [...], "errors": [...]}
    """
    clean_io_files()

    result = {
        "success": False,
        "turns": 0,
        "final_answer": None,
        "tool_calls": [],
        "errors": []
    }

    # 写任务
    with open(os.path.join(IO_DIR, "input.txt"), "w", encoding="utf-8") as f:
        f.write(task)

    # 启动 cli.py --exec 后台进程
    proc = subprocess.Popen(
        [sys.executable, "agent/cli.py", "--exec"],
        cwd=MYAGENT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8"
    )

    try:
        start = time.time()
        max_wait = timeout
        prompt_file = os.path.join(IO_DIR, "prompt.txt")
        response_file = os.path.join(IO_DIR, "response.txt")
        final_file = os.path.join(IO_DIR, "final_answer.txt")

        # 等待 prompt.txt 出现（cli.py 启动后生成）
        print(f"[测试] 等待 prompt.txt 生成...")
        prompt_content = ""
        while time.time() - start < max_wait:
            if os.path.exists(prompt_file):
                content = open(prompt_file, encoding="utf-8").read().strip()
                if content:
                    prompt_content = content
                    break
            time.sleep(0.5)

        if not prompt_content:
            result["errors"].append("prompt.txt 未在超时前出现")
            proc.terminate()
            return result

        # 多轮循环：读prompt → LLM → 写response
        turns = 0
        while time.time() - start < max_wait:
            turns += 1
            print(f"[测试] Turn {turns}: 调用 LLM...")

            llm_resp = call_llm(prompt_content)
            if not llm_resp:
                result["errors"].append(f"Turn {turns}: LLM 调用失败")
                break

            if "tool_calls" in llm_resp:
                result["tool_calls"].extend(llm_resp["tool_calls"])

            # 写 response.txt 通知 cli.py 继续
            with open(response_file, "w", encoding="utf-8") as f:
                json.dump(llm_resp, f, ensure_ascii=False)
            print(f"[测试] Turn {turns}: response.txt 已写入 (action={llm_resp.get('action','?')})")

            # 检查是否 final
            if llm_resp.get("action") == "final":
                result["success"] = True
                result["turns"] = turns
                result["final_answer"] = llm_resp.get("answer", "")
                print(f"[测试] 任务完成 (final_answer: {str(result['final_answer'])[:50]}...)")
                break

            # 等待下一轮 prompt.txt
            time.sleep(1)  # 留时间给 cli.py 执行工具并写新 prompt
            prompt_content = ""
            while time.time() - start < max_wait:
                if os.path.exists(prompt_file):
                    content = open(prompt_file, encoding="utf-8").read().strip()
                    if content and content != prompt_content:
                        prompt_content = content
                        break
                time.sleep(0.5)

            if not prompt_content:
                result["errors"].append(f"Turn {turns}: 等待下一轮 prompt.txt 超时")
                break

        # 等待 final_answer.txt
        elapsed = time.time() - start
        print(f"[测试] 循环结束 ({turns} turns, {elapsed:.1f}s)，检查 final_answer.txt...")
        while time.time() - start < max_wait:
            if os.path.exists(final_file):
                content = open(final_file, encoding="utf-8").read().strip()
                if content:
                    result["final_answer"] = content
                    if not result["success"]:
                        result["success"] = True
                    break
            time.sleep(0.5)

        result["turns"] = turns
        print(f"[测试] 结果: success={result['success']}, turns={result['turns']}, "
              f"final_answer={str(result['final_answer'])[:50] if result['final_answer'] else 'None'}")

    finally:
        # 确保进程结束
        if proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                proc.kill()

        # 打印 cli.py 输出（方便调试）
        stdout, stderr = proc.communicate(timeout=5)
        if stdout:
            for line in stdout.splitlines()[:20]:
                print(f"  [cli] {line}")

    return result


# =============================================================================
# 测试用例（pytest / unittest）
# =============================================================================

class TestE2E(unittest.TestCase):
    """基于真实 LLM + 完整多轮循环的 E2E 测试"""

    def setUp(self):
        clean_io_files()

    def tearDown(self):
        clean_io_files()

    def test_case_1_calc(self):
        """任务1：计算 1+1"""
        task = "请用 python_run 工具计算 1+1 等于几，结果直接输出"
        r = run_full_e2e(task, timeout=180)
        print(f"\n  [结果] {r}")
        self.assertTrue(r["success"], f"任务失败: {r['errors']}")
        self.assertIn("2", str(r["final_answer"]))

    def test_case_2_file_list(self):
        """任务2：列出 MyAgent 目录下的 .py 文件"""
        task = "用 file_list 工具列出 MyAgent 目录下所有 .py 文件（不含子目录），输出前5个文件名的行号"
        r = run_full_e2e(task, timeout=180)
        print(f"\n  [结果] success={r['success']}, turns={r['turns']}, "
              f"tool_calls={len(r['tool_calls'])}, errors={r['errors']}")
        self.assertTrue(r["success"], f"任务失败: {r['errors']}")

    def test_case_3_multiturn(self):
        """任务3：多轮工具调用（file_read + python_run）"""
        task = (
            "1. 用 file_list 列出 MyAgent/io/ 目录下所有文件\n"
            "2. 用 file_read 读取任意一个 .txt 文件前10行\n"
            "3. 输出文件路径和内容行数"
        )
        r = run_full_e2e(task, timeout=240)
        print(f"\n  [结果] success={r['success']}, turns={r['turns']}, "
              f"tool_calls={len(r['tool_calls'])}, errors={r['errors']}")
        self.assertTrue(r["success"], f"任务失败: {r['errors']}")
        self.assertGreaterEqual(r["turns"], 2, "多轮任务需要至少2轮")


if __name__ == "__main__":
    unittest.main(verbosity=2)
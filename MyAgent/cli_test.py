"""
MyAgent CLI 测试 - 直接测试 REPL 流程
======================================
无需 UI，直接：读取 prompt.txt → 调用 LLM → 写入 response.txt

用法:
  python cli_test.py                    # 单次执行
"""
import sys, os, time, json, subprocess, urllib.request

MYAGENT_DIR = r"C:\Users\15041\.openclaw\workspace\MyAgent"
IO_DIR = os.path.join(MYAGENT_DIR, "io")
API_KEY = subprocess.run(
    ['powershell', '-Command', "[Environment]::GetEnvironmentVariable('MINIMAX_API_KEY', 'User')"],
    capture_output=True, text=True, encoding='utf-8'
).stdout.strip()

def call_llm(prompt_text):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": "MiniMax-M2.7",
        "messages": [{"role": "user", "content": prompt_text}],
        "max_tokens": 8192,
        "temperature": 0.7
    }
    req = urllib.request.Request(
        "https://api.minimaxi.com/anthropic/v1/messages",
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

def read_file(path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return open(path, encoding="utf-8").read().strip()
    return ""

def write_file(path, content):
    open(path, "w", encoding="utf-8").write(content)

def main():
    print("=" * 60)
    print("MyAgent CLI 测试")
    print("=" * 60)
    
    prompt_file = os.path.join(IO_DIR, "prompt.txt")
    response_file = os.path.join(IO_DIR, "response.txt")
    final_file = os.path.join(IO_DIR, "final_answer.txt")
    
    # 清空
    for f in [response_file, final_file]:
        if os.path.exists(f):
            open(f, "w", encoding="utf-8").write("")
    
    # 读取 prompt.txt
    prompt = read_file(prompt_file)
    if not prompt:
        print("[错误] prompt.txt 为空")
        print("请先通过 UI 输入任务并点击开始，生成 prompt.txt")
        return
    
    print(f"[读取] prompt.txt ({len(prompt)} chars)")
    print(f"[Prompt 预览] {prompt[:100]}...")
    
    # 调用 LLM
    print("\n[调用] LLM...")
    result = call_llm(prompt)
    
    if not result:
        print("[错误] LLM 调用失败")
        return
    
    print(f"[结果] action={result.get('action')}")
    print(f"[结果] answer={result.get('answer', '')[:100]}")
    
    # 写入 response.txt
    response_json = json.dumps(result, ensure_ascii=False)
    write_file(response_file, response_json)
    print(f"\n[写入] response.txt ({len(response_json)} chars)")
    
    # 如果是 final，写入 final_answer.txt
    if result.get("action") == "final":
        answer = result.get("answer", "")
        write_file(final_file, answer)
        print(f"[完成] final_answer.txt: {answer[:200]}")
    else:
        print(f"[提示] action={result.get('action')}，不是 final")
        print("需要在 MyAgent UI 中点击「粘贴&提交」继续")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
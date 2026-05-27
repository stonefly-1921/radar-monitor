"""
MyAgent LLM 辅助程序
====================
读取 io/prompt.txt → 调用 LLM → 写入 io/response.txt

API key 直接写死在代码里，不需要每次询问。
"""
import json, urllib.request, time

# ===== API 配置 =====
API_KEY = "sk-cp-8BE1wiUugd-zZzIv4Zog8jluRsfL2Esdl6E3d1NudNSXMgaHEvqYySyJpN-UWfJ1B3SHtuc7lFWYqabiiz_VK-seQm-p4U50gFRDHbXJSvc0Dvvcl6XNqh4"
ENDPOINT = "https://api.minimaxi.com/anthropic/v1/messages"
MODEL = "MiniMax-M2.7"

# ===== 路径 =====
MYAGENT_DIR = r"C:\Users\15041\.openclaw\workspace\MyAgent"
IO_DIR = rf"{MYAGENT_DIR}\io"
PROMPT_FILE = rf"{IO_DIR}\prompt.txt"
RESPONSE_FILE = rf"{IO_DIR}\response.txt"
FINAL_FILE = rf"{IO_DIR}\final_answer.txt"


def call_llm(prompt_text: str) -> dict:
    """调用 LLM，返回解析后的 dict"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt_text}],
        "max_tokens": 8192,
        "temperature": 0.7
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=data, headers=headers, method="POST")
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


def read_file(path):
    if __import__("os").path.exists(path):
        size = __import__("os").path.getsize(path)
        if size > 0:
            return open(path, encoding="utf-8").read().strip()
    return ""


def write_file(path, content):
    open(path, "w", encoding="utf-8").write(content)


def main():
    print("=" * 60)
    print("MyAgent LLM 辅助程序")
    print("=" * 60)

    # 读取 prompt.txt
    prompt = read_file(PROMPT_FILE)
    if not prompt:
        print("[提示] prompt.txt 为空，请先在 MyAgent UI 中生成 prompt")
        return

    print(f"[读取] prompt.txt ({len(prompt)} chars)")

    # 调用 LLM
    print("[调用] LLM...")
    result = call_llm(prompt)

    if not result:
        print("[错误] LLM 调用失败")
        return

    print(f"[LLM] action={result.get('action', '?')}")

    # 写入 response.txt
    response_json = json.dumps(result, ensure_ascii=False)
    write_file(RESPONSE_FILE, response_json)
    print(f"[写入] response.txt ({len(response_json)} chars)")

    # 如果是 final action，同时也写到 final_answer.txt
    if result.get("action") == "final":
        answer = result.get("answer", "")
        write_file(FINAL_FILE, answer)
        print(f"[完成] final_answer: {answer[:100]}")

    print("=" * 60)
    print("完成。现在可以在 MyAgent UI 中点击「粘贴&提交」继续。")
    print("=" * 60)


if __name__ == "__main__":
    main()
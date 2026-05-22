"""Test token estimation"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from memory.token_count import count_tokens, total_tokens

tests = [
    # (description, text, expected_range)
    ("空文本", "", 0),
    ("纯中文", "你好世界", 4 * 1.8),
    ("纯英文", "hello world", 11 * 1.25),
    ("中英混合", "Hello 你好 world 世界", 5 * 1.8 + 11 * 1.25),
    ("长中文", "这是一段比较长的中文文本用于测试token估算" * 10, len("这是一段比较长的中文文本用于测试token估算") * 10 * 1.8),
    ("标点符号", "，。；：？！", 6 * 1.8),  # 中文标点被当中文
]

print("=== count_tokens 测试 ===")
all_ok = True
for desc, text, expected in tests:
    result = count_tokens(text)
    ok = result <= expected * 1.1 and result >= expected * 0.9
    status = "PASS" if ok else "WARN"
    print(f"  [{status}] {desc}: {result:.0f} (expect ~{expected:.0f})")

# 测试 total_tokens
print("\n=== total_tokens 测试 ===")
messages = [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "Hello, how can I help you?"},
    {"role": "user", "content": "帮我读取桌面文件"},
]
total = total_tokens(messages)
print(f"  3条消息总 token: {total}")
print(f"  估算合理: {100 < total < 200}")

# 模拟压缩触发
print("\n=== 压缩触发模拟 ===")
MAX_TOKENS = 200000
# 模拟一段长对话
long_content = "这是一段很长的对话内容，假设每轮对话有100个中文字符。" * 100
messages_long = [{"role": "user", "content": long_content}]
total_long = total_tokens(messages_long)
print(f"  100轮 × 100字 ≈ {total_long} tokens")
print(f"  超过 200K: {total_long > MAX_TOKENS}")

print("\n[OK] token 估算测试完成")
"""Token estimation for compression trigger."""
import re


def count_tokens(text: str) -> int:
    """
    估算文本的 token 数（离线计算，无 API 依赖）。
    """
    if not text:
        return 0
    chinese = re.findall(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', text)
    chinese_count = len(chinese)
    english_words = re.findall(r'[a-zA-Z]+', text)
    english_count = sum(len(w) for w in english_words)
    other_count = len(text) - chinese_count - english_count
    return int(chinese_count * 1.8 + english_count * 1.25 + other_count * 0.25)


def total_tokens(messages: list) -> int:
    """计算消息列表的总 token 数。"""
    total = 0
    for msg in messages:
        total += count_tokens(msg.get('content', ''))
        total += 5  # role 前缀
    return total
"""Token estimation for compression trigger."""
import re


def count_tokens(text: str) -> int:
    """
    估算文本的 token 数（离线计算，无 API 依赖）。

    估算规则（近似值，基于中文/英文差异）：
    - 中文字符: ~1.8 tokens/字
    - 英文单词: ~1.25 tokens/词
    - 数字/符号: 酌情计入
    """
    if not text:
        return 0

    # 中文字符（含中文标点）
    chinese = re.findall(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', text)
    chinese_count = len(chinese)

    # 英文单词（连续英文字母）
    english_words = re.findall(r'[a-zA-Z]+', text)
    english_count = sum(len(w) for w in english_words)

    # 其他字符（数字、标点、空白等）
    other_count = len(text) - chinese_count - english_count

    return int(chinese_count * 1.8 + english_count * 1.25 + other_count * 0.25)


def total_tokens(messages: list) -> int:
    """
    计算消息列表的总 token 数。

    Args:
        messages: [{"role": "...", "content": "..."}, ...]

    Returns:
        总 token 估算数
    """
    total = 0
    for msg in messages:
        content = msg.get('content', '')
        total += count_tokens(content)
        # role 前缀也占几个 token
        total += 5
    return total
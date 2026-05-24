# -*- coding: utf-8 -*-
"""Test MiniMax API call with proper error handling."""
import json, urllib.request, os, sys

# Get key from environment
api_key = os.environ.get('MINIMAX_API_KEY', '')
print('API key length:', len(api_key))
print('API key prefix:', api_key[:15] if api_key else 'NONE')

MINIMAX_BASE_URL = "https://api.minimax.chat/v1/text/chatcompletion_v2"

messages = [{"role": "user", "content": "请用一句话介绍自己"}]

payload = {
    "model": "abab5.5-chat",
    "messages": messages,
    "max_tokens": 100
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(
    MINIMAX_BASE_URL,
    data=data,
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    },
    method="POST"
)

print("\nRequest payload:", json.dumps(payload, ensure_ascii=False))
print("Authorization:", f"Bearer {api_key[:20]}...")

try:
    with urllib.request.urlopen(req, timeout=20) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        print("\nStatus:", resp.status)
        print("Full response:", json.dumps(result, indent=2, ensure_ascii=False)[:2000])
except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8')
    print("\nHTTP Error:", e.code, e.reason)
    print("Body:", body[:1000])
except Exception as e:
    print("\nError:", type(e).__name__, str(e))
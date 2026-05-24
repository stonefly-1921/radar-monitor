# -*- coding: utf-8 -*-
"""Test MiniMax via Anthropic-compatible endpoint."""
import json, urllib.request, os

key = open('C:/Users/15041/.openclaw/workspace/MyAgent/_apikey.txt').read().strip()

# Try MiniMax Anthropic-compatible endpoint (what OpenClaw uses)
url = 'https://api.minimaxi.com/anthropic/v1/messages'

headers = {
    'Authorization': 'Bearer ' + key,
    'Content-Type': 'application/json',
    'anthropic-version': '2023-06-01'
}

messages = [{'role': 'user', 'content': '请用一句话介绍自己'}]

payload = {
    'model': 'MiniMax-M2.7',
    'messages': messages,
    'max_tokens': 100
}

data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(url, data=data, headers=headers, method='POST')

print('Testing Anthropic endpoint:', url)
print('Model: MiniMax-M2.7')
try:
    with urllib.request.urlopen(req, timeout=20) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        print('Status:', resp.status)
        print('Response:', json.dumps(result, indent=2, ensure_ascii=False)[:1000])
except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8')
    print('HTTP Error:', e.code)
    print('Body:', body[:1000])
except Exception as e:
    print('Error:', type(e).__name__, str(e))
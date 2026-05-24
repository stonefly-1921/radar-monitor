# -*- coding: utf-8 -*-
import json, urllib.request, os

key = open('C:/Users/15041/.openclaw/workspace/MyAgent/_apikey.txt').read().strip()
url = 'https://api.minimaxi.com/anthropic/v1/messages'
headers = {
    'Authorization': 'Bearer ' + key,
    'Content-Type': 'application/json',
    'anthropic-version': '2023-06-01'
}

# Test 1: Simple call with high max_tokens
print("Test 1: Simple call")
payload = {'model': 'MiniMax-M2.7', 'messages': [{'role': 'user', 'content': '1+1等于几？用一句话回答。'}], 'max_tokens': 200}
data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(url, data=data, headers=headers, method='POST')
try:
    with urllib.request.urlopen(req, timeout=20) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        print('Status:', resp.status)
        content = result.get('content', [])
        usage = result.get('usage', {})
        print('Content:', content)
        print('Usage:', usage)
        print('Full:', json.dumps(result, ensure_ascii=False)[:500])
except Exception as e:
    print('Error:', e)

print()

# Test 2: With system prompt
print("Test 2: With system prompt")
payload2 = {
    'model': 'MiniMax-M2.7',
    'messages': [
        {'role': 'system', 'content': '你是一个有帮助的助手。'},
        {'role': 'user', 'content': '1+1等于几？'}
    ],
    'max_tokens': 200
}
data2 = json.dumps(payload2).encode('utf-8')
req2 = urllib.request.Request(url, data=data2, headers=headers, method='POST')
try:
    with urllib.request.urlopen(req2, timeout=20) as resp:
        result2 = json.loads(resp.read().decode('utf-8'))
        content2 = result2.get('content', [])
        print('Content:', content2)
        if content2:
            print('Text:', content2[0].get('text', ''))
except Exception as e:
    print('Error:', e)
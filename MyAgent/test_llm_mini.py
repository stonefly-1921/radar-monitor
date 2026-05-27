"""最小化 LLM 调用测试"""
import json, subprocess, urllib.request

api_key = subprocess.run(
    ['powershell', '-Command', '[Environment]::GetEnvironmentVariable("MINIMAX_API_KEY", "User")'],
    capture_output=True, text=True, encoding='utf-8'
).stdout.strip()

print(f'API key: {api_key[:15]}...' if api_key else 'API key: (empty)')

url = 'https://api.minimaxi.com/anthropic/v1/messages'
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json',
    'anthropic-version': '2023-06-01',
}
payload = {
    'model': 'MiniMax-M2.7',
    'messages': [{'role': 'user', 'content': '请计算 1+1 等于几'}],
    'max_tokens': 1024,
    'temperature': 0.7
}
data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(url, data=data, headers=headers, method='POST')

print('Calling LLM...')
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        for item in result.get('content', []):
            if item.get('type') == 'text':
                print(f'Result: {item.get("text", "")[:200]}')
except Exception as e:
    print(f'Error: {e}')

print('Done')
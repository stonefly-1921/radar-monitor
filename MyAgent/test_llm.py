import subprocess, urllib.request, json

result = subprocess.run(
    ['powershell', '-Command', '[Environment]::GetEnvironmentVariable("MINIMAX_API_KEY", "User")'],
    capture_output=True, text=True, encoding='utf-8'
)
api_key = result.stdout.strip()
print(f'Key: {api_key[:15]}...')

url = 'https://api.minimaxi.com/anthropic/v1/messages'
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json',
    'anthropic-version': '2023-06-01',
}
payload = {
    'model': 'MiniMax-M2.7',
    'messages': [{'role': 'user', 'content': '1+1=? Respond in JSON: {"answer": "..."}'}],
    'max_tokens': 100,
    'temperature': 0.7
}
data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(url, data=data, headers=headers, method='POST')
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        result_data = json.loads(resp.read().decode('utf-8'))
        print(f'Success: {result_data}')
except Exception as e:
    print(f'Error: {e}')
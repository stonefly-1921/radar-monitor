import subprocess, urllib.request, json

result = subprocess.run(
    ['powershell', '-Command', '[Environment]::GetEnvironmentVariable("MINIMAX_API_KEY", "User")'],
    capture_output=True, text=True, encoding='utf-8'
)
api_key = result.stdout.strip()

url = 'https://api.minimaxi.com/anthropic/v1/messages'
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json',
    'anthropic-version': '2023-06-01',
}

prompt = open(r'C:\Users\15041\.openclaw\workspace\MyAgent\io\prompt.txt', encoding='utf-8').read().strip()

payload = {
    'model': 'MiniMax-M2.7',
    'messages': [{'role': 'user', 'content': prompt}],
    'max_tokens': 8192,
    'temperature': 0.7
}
data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(url, data=data, headers=headers, method='POST')
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        result_data = json.loads(resp.read().decode('utf-8'))
        content = result_data.get('content', [])
        for i, item in enumerate(content):
            print(f'[{i}] type={item.get("type")}')
            if item.get('type') == 'text':
                print(f'    text: {item.get("text", "")[:500]}')
            elif item.get('type') == 'thinking':
                print(f'    thinking: {item.get("thinking", "")[:200]}')
except Exception as e:
    print(f'Error: {e}')
    import traceback; traceback.print_exc()
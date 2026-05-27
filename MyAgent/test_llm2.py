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
print(f'Prompt length: {len(prompt)}')
print(f'Prompt preview: {prompt[:200]}')

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
        print(f'Content type: {type(content)}, length: {len(content)}')
        if content:
            print(f'First item type: {content[0].get("type")}')
            if content[0].get('type') == 'text':
                print(f'Text: {content[0].get("text", "")[:300]}')
            elif content[0].get('type') == 'thinking':
                print(f'Thinking: {content[0].get("thinking", "")[:300]}')
except Exception as e:
    print(f'Error: {e}')
    import traceback; traceback.print_exc()
"""测试 LLM 调用 + 写 response.txt + 触发提交"""
import sys, os, time, json, subprocess, urllib.request

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'
IO_DIR = os.path.join(MYAGENT_DIR, 'io')

# 1. 读取 API key
api_key = subprocess.run(
    ['powershell', '-Command', '[Environment]::GetEnvironmentVariable("MINIMAX_API_KEY", "User")'],
    capture_output=True, text=True, encoding='utf-8'
).stdout.strip()
print(f'API key: {api_key[:15]}...' if api_key else 'API key: (empty)')

# 2. 清空 io
for f in ['response.txt', 'final_answer.txt']:
    p = os.path.join(IO_DIR, f)
    if os.path.exists(p):
        open(p, 'w', encoding='utf-8').write('')
print('[清空] response.txt, final_answer.txt')

# 3. 读 prompt.txt
prompt_path = os.path.join(IO_DIR, 'prompt.txt')
prompt = ''
if os.path.exists(prompt_path) and os.path.getsize(prompt_path) > 0:
    prompt = open(prompt_path, encoding='utf-8').read().strip()
print(f'[Prompt] 长度={len(prompt)}')

# 4. 调用 LLM
print('[LLM] 调用...')
url = 'https://api.minimaxi.com/anthropic/v1/messages'
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json',
    'anthropic-version': '2023-06-01',
}
payload = {
    'model': 'MiniMax-M2.7',
    'messages': [{'role': 'user', 'content': prompt}],
    'max_tokens': 8192,
    'temperature': 0.7
}
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode('utf-8'),
    headers=headers,
    method='POST'
)
result_data = None
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        for item in result.get('content', []):
            if item.get('type') == 'text':
                text = item.get('text', '').strip()
                if text:
                    try:
                        result_data = json.loads(text)
                    except:
                        result_data = {'action': 'final', 'answer': text}
except Exception as e:
    print(f'[LLM] 错误: {e}')
    sys.exit(1)

print(f'[LLM] 结果: action={result_data.get("action", "?")}, answer={result_data.get("answer", "")[:50]}')

# 5. 写 response.txt
response_json = json.dumps(result_data, ensure_ascii=False)
resp_path = os.path.join(IO_DIR, 'response.txt')
open(resp_path, 'w', encoding='utf-8').write(response_json)
print(f'[写文件] response.txt 已写入 {len(response_json)} chars')

# 6. 等待 REPL 处理（20秒）
print('[等待] 20秒让 REPL 处理...')
time.sleep(20)

# 7. 检查结果
print('[结果]')
for f in ['input.txt', 'prompt.txt', 'response.txt', 'final_answer.txt']:
    p = os.path.join(IO_DIR, f)
    if os.path.exists(p):
        size = os.path.getsize(p)
        content = open(p, encoding='utf-8').read().strip()[:80] if size > 0 else ''
        print(f'  {f}: {size}B | {content}')
    else:
        print(f'  {f}: (不存在)')

print('[完成]')
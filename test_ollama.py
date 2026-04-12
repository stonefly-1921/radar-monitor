"""测试 ollama qwen3:4b-instruct"""
import urllib.request, json, time

# Test simple Ollama call
t0 = time.time()
body = json.dumps({
    'model': 'qwen3:4b-instruct',
    'prompt': '回复OK',
    'stream': False,
    'options': {'num_predict': 20}
}).encode()
req = urllib.request.Request(
    'http://127.0.0.1:11434/api/generate',
    data=body,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
resp = urllib.request.urlopen(req, timeout=30)
data = json.loads(resp.read())
print(f'Ollama耗时: {time.time()-t0:.1f}s')
print('response:', data.get('response', '')[:100])

# Now test the agent_loop.chat() directly
import sys
sys.path.insert(0, r'E:\radar-brain-github\backend')
sys.path.insert(0, r'E:\radar-brain-github\agent')

print("\nTesting agent_loop.chat()...")
from agent_loop import AgentLoop
loop = AgentLoop()
t0 = time.time()
result = loop.chat("TAS跟踪1号目标", session_id="test")
print(f"chat()耗时: {time.time()-t0:.1f}s")
print('result:', str(result)[:200])

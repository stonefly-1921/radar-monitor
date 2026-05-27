"""
10个通用任务测试 - 简化为单轮快速测试
======================================
只测试 prompt -> LLM -> response 流程
快速验证 LLM 响应格式是否正确
"""
import time, json, subprocess, urllib.request, os

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'
IO_DIR = rf'{MYAGENT_DIR}\io'
API_KEY = subprocess.run(
    ['powershell', '-Command', "[Environment]::GetEnvironmentVariable('MINIMAX_API_KEY', 'User')"],
    capture_output=True, text=True, encoding='utf-8'
).stdout.strip()


def call_llm(prompt_text):
    url = 'https://api.minimaxi.com/anthropic/v1/messages'
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json',
        'anthropic-version': '2023-06-01',
    }
    payload = {
        'model': 'MiniMax-M2.7',
        'messages': [{'role': 'user', 'content': prompt_text}],
        'max_tokens': 8192,
        'temperature': 0.7
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        for item in result.get('content', []):
            if item.get('type') == 'text':
                text = item.get('text', '').strip()
                if text:
                    try:
                        return json.loads(text)
                    except:
                        return {'action': 'final', 'answer': text}


# 读取 prompt.txt 并测试 LLM 响应
print('=' * 60)
print('10个任务快速测试 - LLM 响应格式验证')
print('=' * 60)

prompt_file = os.path.join(IO_DIR, 'prompt.txt')
if os.path.exists(prompt_file) and os.path.getsize(prompt_file) > 0:
    prompt = open(prompt_file, encoding='utf-8').read().strip()
    print(f'\n[读取] prompt.txt ({len(prompt)} chars)')
    
    print('\n[调用] LLM...')
    result = call_llm(prompt)
    
    if result:
        action = result.get('action', '?')
        print(f'  action={action}')
        
        if action == 'final':
            answer = result.get('answer', '')
            print(f'  answer={answer[:100]}...' if len(answer) > 100 else f'  answer={answer}')
            
            # 检查 answer 是否是纯文本（不是 JSON 字符串）
            try:
                json.loads(answer)
                print('  [警告] answer 是 JSON 字符串，应该提取实际内容')
            except:
                print('  [OK] answer 是纯文本')
        elif action == 'tool_call':
            tools = result.get('tools', [])
            print(f'  tools={len(tools)} 个')
            for t in tools[:3]:
                print(f'    - {t.get("tool")}: {str(t.get("params"))[:80]}')
    else:
        print('  [失败] LLM 调用失败')
else:
    print('[跳过] prompt.txt 为空')

# 也直接测试一个简单任务
print('\n\n[额外测试] 直接测试简单任务: 1+1=2')
simple_prompt = '''你是 MyAgent，一个智能助手。

当前任务：请计算 1+1 等于几

请直接输出最终答案，不要输出其他内容。

输出格式（严格 JSON）：
{"action": "final", "answer": "你的最终答案"}
'''

result = call_llm(simple_prompt)
if result:
    action = result.get('action', '?')
    print(f'  action={action}')
    if action == 'final':
        answer = result.get('answer', '')
        print(f'  answer={answer}')
        if '2' in answer:
            print('  [OK] 包含正确答案 2')
        else:
            print('  [警告] 可能不是正确答案')
    elif action == 'tool_call':
        print(f'  [需要工具] {result.get("tools")}')
else:
    print('  [失败]')

print('\n' + '=' * 60)
print('测试完成')
print('=' * 60)
import json

path = r'C:\Users\15041\.openclaw\agents\main\sessions\65b930f5-5c6d-4846-a97a-e3500671cd9d.jsonl'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Look at lines 40-50 for context about earlier conversation
for i in range(40, 55):
    try:
        msg = json.loads(lines[i])
        ts = msg.get('timestamp','')
        role = msg.get('message',{}).get('role','')
        content = msg.get('message',{}).get('content',[])
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get('type') == 'text':
                    text = item.get('text','')[:300]
                    if text.strip():
                        print(f'[{i}] {ts} [{role}]: {text[:280]}')
                        print('---')
    except:
        pass
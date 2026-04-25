import json, os, glob

# Search all session files for "桌面" or "bertopic" mentions
session_dir = r'C:\Users\15041\.openclaw\agents\main\sessions'
files = glob.glob(os.path.join(session_dir, '*.jsonl'))

for fp in files:
    try:
        content = open(fp, 'r', encoding='utf-8', errors='ignore').read()
        if any(k in content for k in ['桌面', 'bertopic', 'BERTopic', 'Desktop']):
            fname = os.path.basename(fp)
            print(f'=== {fname} ===')
            # Find first occurrence
            for line in content.split('\n'):
                if any(k in line for k in ['桌面', 'bertopic', 'BERTopic', 'Desktop']):
                    try:
                        msg = json.loads(line)
                        ts = msg.get('timestamp','')
                        role = msg.get('message',{}).get('role','')
                        content2 = msg.get('message',{}).get('content',[])
                        if isinstance(content2, list):
                            for item in content2:
                                if isinstance(item, dict) and item.get('type') == 'text':
                                    text = item.get('text','')[:200]
                                    if any(k in text for k in ['桌面', 'bertopic', 'BERTopic', 'Desktop']):
                                        print(f'  [{ts}] [{role}]: {text[:180]}')
                                        break
                    except:
                        pass
            print()
    except Exception as e:
        pass
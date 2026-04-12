content = open(r'E:\radar-brain-github\agent\plan_parser.py', encoding='utf-8', errors='ignore').read()
idx = content.find('如果指令涉及')
if idx >= 0:
    print(content[idx:idx+4000])
else:
    print('NOT FOUND')
    # Try to find the prompt section
    idx2 = content.find('prompt')
    print(f'prompt at {idx2}')
    print(content[idx2:idx2+3000])

content = open(r'E:\radar-brain-github\agent\plan_parser.py', encoding='utf-8', errors='ignore').read()
idx = content.find('如果指令涉及')
print(content[idx:idx+3000])

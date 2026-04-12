content = open(r'E:\radar-brain-github\agent\plan_parser.py', encoding='utf-8', errors='ignore').read()
print(len(content), 'chars')
for keyword in ['开机', 'power', '先', '如果', 'IF']:
    idx = content.find(keyword)
    if idx >= 0:
        print(f'--- {keyword!r} at {idx} ---')
        print(content[max(0,idx-100):idx+300])
        print()

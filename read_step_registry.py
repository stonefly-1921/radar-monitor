content = open(r'E:\radar-brain-github\agent\step_registry.py', encoding='utf-8', errors='ignore').read()
# Find TasEngageStep class
idx = content.find('class TasEngageStep')
print(repr(content[idx:idx+2000]))

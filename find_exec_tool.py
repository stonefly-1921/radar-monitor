content = open(r'E:\radar-brain-github\agent\agent_loop.py', encoding='utf-8', errors='ignore').read()
idx = content.find('def execute_tool')
print(f"Found at: {idx}")
print(content[idx:idx+1000])

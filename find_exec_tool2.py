content = open(r'E:\radar-brain-github\agent\agent_loop.py', encoding='utf-8', errors='ignore').read()
# Find execute_tool fallback
idx = content.find('# fallback：直接遍历')
print(f"Fallback at: {idx}")
print(content[idx:idx+600])

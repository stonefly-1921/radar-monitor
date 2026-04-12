"""修复 agent_loop.py 中的 emoji 问题"""
path = r'E:\radar-brain-github\agent\agent_loop.py'
content = open(path, encoding='utf-8', errors='ignore').read()

replacements = {
    '\u2705': '[OK]',
    '\u274c': '[FAIL]',
    '\u26a0': '[WARN]',
    '\u2714': '[OK]',
    '\u2716': '[FAIL]',
    '\u25b6': '[>]',
    '\u2713': '[V]',
    '\u2192': '->',
    '\u2190': '<-',
    '\u2b06': '[UP]',
    '\u2b07': '[DN]',
    '\u27a1': '[->]',
}

changed = 0
for old, new in replacements.items():
    if old in content:
        cnt = content.count(old)
        print(f"Replacing {cnt}x U+{ord(old):04X} with {repr(new)}")
        content = content.replace(old, new)
        changed += cnt

if changed:
    with open(path, 'w', encoding='utf-8', errors='replace') as f:
        f.write(content)
    print(f"Done! {changed} replacements made.")
else:
    print("No emoji found.")

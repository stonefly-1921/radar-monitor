"""Verify plan_config.yaml template is correctly UTF-8 encoded"""
import yaml

with open(r'E:\radar-brain-github\agent\plan_config.yaml', encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

tpl = cfg['system_prompt_template']
print('Template length:', len(tpl))
print('First 200 bytes (repr):')
print(repr(tpl[:200]))
print()
# Check for the key phrases
checks = [
    '定方位监视指令拆解',
    '转动模式',
    'set_mode(mode=stop)',
    'set_steer',
]
for c in checks:
    found = c in tpl
    print(f'"{c}": {"FOUND" if found else "MISSING"}')

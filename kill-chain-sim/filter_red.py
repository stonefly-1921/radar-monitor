with open('src/main.py', 'r') as f:
    content = f.read()

old_filter = '''        for entity in entities:
            if entity.category_name == "AIR":
                targets.append(Target('''

new_filter = '''        for entity in entities:
            if entity.category_name == "AIR" and entity.force_side == "red":
                targets.append(Target('''

if old_filter in content:
    content = content.replace(old_filter, new_filter)
    with open('src/main.py', 'w') as f:
        f.write(content)
    print('Replacement successful')
else:
    print('Pattern not found')

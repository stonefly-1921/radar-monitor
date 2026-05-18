with open('src/core/dis/entity_tracker.py', 'r') as f:
    content = f.read()

# Find the end of category_name property and add force_side after it
old_text = '''        return "UNKNOWN"

    # Entity side (force: blue friendly, red hostile, neutral)
    # DIS has no explicit force ID field, so we derive it from entity_type.extra
    # In AFSIM: extra=1 often means blue/friendly, extra=2 means red/hostile
    @property
    def force_side(self) -> str:
        """Force side (blue/red/neutral) derived from entity type extra field."""
        if self.entity_type.extra == 1:
            return "blue"
        elif self.entity_type.extra == 2:
            return "red"
        return "neutral"

'''

new_text = '''        return "UNKNOWN"

    # Entity side (force: blue friendly, red hostile, neutral)
    # DIS has no explicit force ID field, so we derive it from entity_type.extra
    # In AFSIM: extra=1 often means blue/friendly, extra=2 means red/hostile
    @property
    def force_side(self) -> str:
        """Force side (blue/red/neutral) derived from entity type extra field."""
        if self.entity_type.extra == 1:
            return "blue"
        elif self.entity_type.extra == 2:
            return "red"
        return "neutral"

'''

if old_text in content:
    content = content.replace(old_text, new_text)
    with open('src/core/dis/entity_tracker.py', 'w') as f:
        f.write(content)
    print('Replacement successful')
else:
    print('Pattern not found')

with open('src/core/dis/entity_tracker.py', 'r') as f:
    content = f.read()

# Find the last occurrence of 'return "UNKNOWN"'
idx = content.rfind('return "UNKNOWN"')
if idx >= 0:
    print(f'Found at {idx}')
    print('Context:')
    print(repr(content[idx:idx+100]))
    
    # Find the class closing and insert after
    # The property ends at the next blank line after return UNKNOWN
    end_idx = content.find('\n\n', idx)
    if end_idx >= 0:
        print(f'Property ends at {end_idx}')
        
        new_property = '''

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
        content = content[:end_idx+2] + new_property + content[end_idx+2:]
        with open('src/core/dis/entity_tracker.py', 'w') as f:
            f.write(content)
        print('Replacement successful')
else:
    print('Pattern not found')

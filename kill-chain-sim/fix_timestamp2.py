with open('src/core/dis/dis_protocol.py', 'r') as f:
    content = f.read()

# Change format
content = content.replace('DIS_TIMESTAMP_FORMAT = ">BI"  # 5 bytes', 'DIS_TIMESTAMP_FORMAT = ">I"  # 4 bytes (uint32 seconds since hour)')
content = content.replace('DIS_TIMESTAMP_SIZE = 5', 'DIS_TIMESTAMP_SIZE = 4')

# Replace the DisTimestamp class entirely
import re
pattern = r'class DisTimestamp:.*?(?=\nclass |\n@dataclass |\Z)'
m = re.search(pattern, content, re.DOTALL)
if m:
    new_class = '''class DisTimestamp:
    """DIS Timestamp (4 bytes): seconds since top of hour (uint32).
    
    This is a simplified format. IEEE 1278.1 defines a 48-bit timestamp,
    but many DIS implementations use 4 bytes (uint32) for seconds since hour.
    """
    seconds: int

    def encode(self) -> bytes:
        return struct.pack(DIS_TIMESTAMP_FORMAT, self.seconds % 3600)

    @classmethod
    def decode(cls, data: bytes) -> 'DisTimestamp':
        seconds = struct.unpack(DIS_TIMESTAMP_FORMAT, data[:DIS_TIMESTAMP_SIZE])[0]
        return cls(seconds=seconds)

    @classmethod
    def from_seconds(cls, seconds_since_hour: float) -> 'DisTimestamp':
        return cls(seconds=int(seconds_since_hour) % 3600)

    def to_seconds(self) -> float:
        return float(self.seconds)

    @classmethod
    def now(cls) -> 'DisTimestamp':
        import time
        t = time.time()
        hour_sec = (int(t) % 86400)
        return cls(seconds=hour_sec % 3600)

'''
    content = content[:m.start()] + new_class + content[m.end():]
    print('Replaced DisTimestamp class')
else:
    print('DisTimestamp class not found')

with open('src/core/dis/dis_protocol.py', 'w') as f:
    f.write(content)
print('Done')

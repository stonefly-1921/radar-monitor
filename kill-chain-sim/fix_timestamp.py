with open('src/core/dis/dis_protocol.py', 'r') as f:
    content = f.read()

# Fix 1: Change DIS_TIMESTAMP_FORMAT to 4 bytes (uint32)
old_ts_format = 'DIS_TIMESTAMP_FORMAT = ">BI"  # 5 bytes'
new_ts_format = 'DIS_TIMESTAMP_FORMAT = ">I"  # 4 bytes (uint32 seconds since hour)'

# Fix 2: Change DIS_TIMESTAMP_SIZE
old_ts_size = 'DIS_TIMESTAMP_SIZE = 5'
new_ts_size = 'DIS_TIMESTAMP_SIZE = 4'

# Fix 3: Update DisTimestamp class
old_class = '''class DisTimestamp:
    """DIS Timestamp (5 bytes): hours (0-23) + time (centiseconds since hour)."""
    hours: int       # uint8 (0-23)
    time: int        # uint32 (centiseconds since top of hour)

    def encode(self) -> bytes:
        return struct.pack(DIS_TIMESTAMP_FORMAT, self.hours, self.time)

    @classmethod
    def decode(cls, data: bytes) -> 'DisTimestamp':
        hours, time_val = struct.unpack(DIS_TIMESTAMP_FORMAT, data[:DIS_TIMESTAMP_SIZE])
        return cls(hours=hours, time_val=time_val)

    @classmethod
    def from_seconds(cls, seconds_since_hour: float) -> 'DisTimestamp':
        """Create timestamp from seconds since top of hour."""
        hours = int(seconds_since_hour) // 3600
        hours = hours % 24
        centis = int((seconds_since_hour % 3600) * 100)
        return cls(hours=hours, time=centis)

    def to_seconds(self) -> float:
        """Convert to seconds since top of hour."""
        return self.hours * 3600.0 + self.time * 0.01

    @classmethod
    def now(cls) -> 'DisTimestamp':
        """Create timestamp for current time."""
        import time
        t = time.time()
        hour_sec = (int(t) % 86400)  # seconds since midnight
        cs = int((t % 1.0) * 100)
        return cls(hours=hour_sec // 3600, time=cs)'''

new_class = '''class DisTimestamp:
    """DIS Timestamp (4 bytes): seconds since top of hour (uint32).
    
    This is a simplified format. IEEE 1278.1 defines a 48-bit timestamp,
    but many DIS implementations use 4 bytes (uint32) for seconds since hour.
    """
    seconds: int       # uint32 (seconds since top of hour, modulo 3600)

    def encode(self) -> bytes:
        return struct.pack(DIS_TIMESTAMP_FORMAT, self.seconds % 3600)

    @classmethod
    def decode(cls, data: bytes) -> 'DisTimestamp':
        seconds = struct.unpack(DIS_TIMESTAMP_FORMAT, data[:DIS_TIMESTAMP_SIZE])[0]
        return cls(seconds=seconds)

    @classmethod
    def from_seconds(cls, seconds_since_hour: float) -> 'DisTimestamp':
        """Create timestamp from seconds since top of hour."""
        return cls(seconds=int(seconds_since_hour) % 3600)

    def to_seconds(self) -> float:
        """Convert to seconds since top of hour."""
        return float(self.seconds)

    @classmethod
    def now(cls) -> 'DisTimestamp':
        """Create timestamp for current time."""
        import time
        t = time.time()
        hour_sec = (int(t) % 86400)  # seconds since midnight
        return cls(seconds=hour_sec % 3600)'''

if old_ts_format in content:
    content = content.replace(old_ts_format, new_ts_format)
    print('Fixed timestamp format')
else:
    print('ERROR: Could not find timestamp format string')

if old_ts_size in content:
    content = content.replace(old_ts_size, new_ts_size)
    print('Fixed timestamp size')
else:
    print('ERROR: Could not find timestamp size')

if 'class DisTimestamp:' in content:
    # Find and replace the whole class
    import re
    pattern = r'class DisTimestamp:.*?(?=\nclass |\n@dataclass |\Z)'
    m = re.search(pattern, content, re.DOTALL)
    if m:
        old_class_text = m.group(0)
        # Extract the class name and next class
        next_class_match = re.search(r'(\nclass \w+:)', content[m.end():])
        next_class_marker = next_class_match.group(1) if next_class_match else ''
        
        new_class_text = '''class DisTimestamp:
    """DIS Timestamp (4 bytes): seconds since top of hour (uint32).
    
    This is a simplified format. IEEE 1278.1 defines a 48-bit timestamp,
    but many DIS implementations use 4 bytes (uint32) for seconds since hour.
    """
    seconds: int       # uint32 (seconds since top of hour, modulo 3600)

    def encode(self) -> bytes:
        return struct.pack(DIS_TIMESTAMP_FORMAT, self.seconds % 3600)

    @classmethod
    def decode(cls, data: bytes) -> 'DisTimestamp':
        seconds = struct.unpack(DIS_TIMESTAMP_FORMAT, data[:DIS_TIMESTAMP_SIZE])[0]
        return cls(seconds=seconds)

    @classmethod
    def from_seconds(cls, seconds_since_hour: float) -> 'DisTimestamp':
        """Create timestamp from seconds since top of hour."""
        return cls(seconds=int(seconds_since_hour) % 3600)

    def to_seconds(self) -> float:
        """Convert to seconds since top of hour."""
        return float(self.seconds)

    @classmethod
    def now(cls) -> 'DisTimestamp':
        """Create timestamp for current time."""
        import time
        t = time.time()
        hour_sec = (int(t) % 86400)  # seconds since midnight
        return cls(seconds=hour_sec % 3600)
'''
        content = content[:m.start()] + new_class_text + content[m.end():]
        print('Fixed DisTimestamp class')
    else:
        print('ERROR: Could not find DisTimestamp class')
else:
    print('ERROR: DisTimestamp class not found')

with open('src/core/dis/dis_protocol.py', 'w') as f:
    f.write(content)
print('Done')

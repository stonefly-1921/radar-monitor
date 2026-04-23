import os

# Read raw bytes of message_0.db
db_path = r'C:\Users\15041\xwechat_files\wshjustin_3dff\db_storage\message\message_0.db'
with open(db_path, 'rb') as f:
    data = f.read(80)

print(f'First 80 bytes hex: {data.hex()}')
print(f'First 16 bytes: {data[:16].hex()}')
print(f'Is SQLite header? {data[:16] == b"SQLite format 3"}')
print(f'Is WCDB salt? Salt is 16 bytes: {data[:16].hex()}')

# Known salt for message_0.db: 0c60d940ad4890ed954927b20c051c4a
known_salt = bytes.fromhex('0c60d940ad4890ed954927b20c051c4a')
print(f'\nKnown salt: {known_salt.hex()}')
print(f'Matches first 16 bytes? {data[:16] == known_salt}')

# If first 16 bytes = salt, then bytes 16-48 = enc_key (32 bytes)
print(f'\nBytes 16-48 (potential enc_key): {data[16:48].hex()}')
print(f'Length: {len(data[16:48])} bytes')

# If first 16 = salt, bytes 48-80 = ?
print(f'Bytes 48-80: {data[48:80].hex()}')
print(f'File size: {os.path.getsize(db_path)} bytes')

# Read last 80 bytes
with open(db_path, 'rb') as f:
    f.seek(0, 2)  # end
    f.seek(-80, 2)  # 80 bytes from end
    last80 = f.read()
print(f'\nLast 80 bytes: {last80.hex()}')

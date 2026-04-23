import sqlite3

key_db = r'C:\Users\15041\xwechat_files\all_users\login\wshjustin\key_info.db'
conn = sqlite3.connect(key_db)
c = conn.cursor()
c.execute("SELECT user_name_md5, key_info_md5, key_info_data FROM LoginKeyInfoTable")
rows = c.fetchall()
conn.close()

# The key_info_data is a protobuf. Let's try to find 32-byte (64 hex) and 16-byte (32 hex) patterns
known_salt = '0c60d940ad4890ed954927b20c051c4a'  # message_0.db salt
known_key = 'ce21fdd6ae57c1f23cc4ce3e315ff857138773906331833f7f30a8e613dfab16'  # message_0.db key from memory

for i, (uin_md5, key_md5, data) in enumerate(rows):
    print(f'=== Row {i} ===')
    print(f'  uin_md5: {uin_md5}')
    print(f'  key_md5: {key_md5}')
    h = data.hex()
    print(f'  key_info_data ({len(data)} bytes): {h}')
    
    # Scan for 32-char hex strings (potential keys)
    for j in range(0, len(h) - 64 + 1, 2):
        candidate = h[j:j+64]
        if all(c in '0123456789abcdef' for c in candidate):
            # Check if it's a potential key
            pass  # too slow, skip
    
    # Check if known key/salt in data
    if known_salt in h:
        print(f'  ** Contains known salt! **')
    if known_key in h:
        print(f'  ** Contains known enc_key! **')
    
    # Check last 32 bytes as potential key
    last32 = h[-64:]
    print(f'  Last 32 bytes: {last32}')
    last16 = h[-32:]
    print(f'  Last 16 bytes: {last16}')
    
    # Check first 32 bytes  
    first32 = h[:64]
    print(f'  First 32 bytes: {first32}')
    print()

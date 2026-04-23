"""
Bypass HMAC verification, try direct AES decryption of SQLCipher 4 page
"""
import hashlib
import struct
import os
from Crypto.Cipher import AES

PAGE_SZ = 4096
KEY_SZ = 32
SALT_SZ = 16
IV_SZ = 16
HMAC_SZ = 64
RESERVE_SZ = 80  # IV(16) + HMAC(64)

# From all_keys.json for message_0.db
enc_key = bytes.fromhex('ce21fdd6ae57c1f23cc4ce3e315ff857138773906331833f7f30a8e613dfab16')
salt = bytes.fromhex('0c60d940ad4890ed954927b20c051c4a')

db_path = r'C:\Users\15041\xwechat_files\wshjustin_3dff\db_storage\message\message_0.db'

with open(db_path, 'rb') as f:
    page1 = f.read(PAGE_SZ)

# Derive decryption key: enc_key + salt -> PBKDF2-SHA512 with 256000 iterations
dk = hashlib.pbkdf2_hmac("sha512", enc_key, salt, 256000, dklen=64)
cipher_key = dk[:32]  # first 32 bytes for AES
mac_key = dk[32:]     # last 32 bytes

# IV is at bytes 4016-4031 (PAGE_SZ - RESERVE_SZ to PAGE_SZ - RESERVE_SZ + IV_SZ)
iv_start = PAGE_SZ - RESERVE_SZ
iv = page1[iv_start : iv_start + IV_SZ]
print(f'IV: {iv.hex()}')

# Encrypted data is from byte 16 to byte 4016 (SALT_SZ to iv_start)
enc_data = page1[SALT_SZ : iv_start]
print(f'Encrypted data: {len(enc_data)} bytes, starts: {enc_data[:32].hex()}')

# Decrypt
cipher = AES.new(cipher_key, AES.MODE_CBC, iv)
decrypted = cipher.decrypt(enc_data)
print(f'Decrypted: {len(decrypted)} bytes')
print(f'Decrypted starts: {decrypted[:32].hex()}')
print(f'Is SQLite header? {decrypted[:16] == b"SQLite format 3"}')

# Check padding
pad_len = decrypted[-1]
print(f'Last byte (pad len?): {pad_len}, valid? {1 <= pad_len <= 16}')
print(f'Decrypted ends: {decrypted[-32:].hex()}')

# Try to verify
if decrypted[:16] == b'SQLite format 3':
    print('\n✅ DECRYPTION SUCCESS! Data is valid SQLite!')
    # Save decrypted page 1
    out_path = r'C:\Users\15041\Desktop\wechat-decrypt\decrypted\message_0_page1.db'
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(decrypted)
    print(f'Saved first page to {out_path}')
else:
    print('\n❌ Decryption failed - data not valid SQLite')

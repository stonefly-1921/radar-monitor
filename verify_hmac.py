import hashlib
import hmac as hmac_mod
import struct
import os
from Crypto.Cipher import AES

PAGE_SZ = 4096
KEY_SZ = 32
SALT_SZ = 16
IV_SZ = 16
HMAC_SZ = 64
RESERVE_SZ = 80

enc_key = bytes.fromhex('ce21fdd6ae57c1f23cc4ce3e315ff857138773906331833f7f30a8e613dfab16')
salt = bytes.fromhex('0c60d940ad4890ed954927b20c051c4a')

db_path = r'C:\Users\15041\xwechat_files\wshjustin_3dff\db_storage\message\message_0.db'
with open(db_path, 'rb') as f:
    page1 = f.read(PAGE_SZ)

# Derive MAC key
mac_salt = bytes(b ^ 0x3a for b in salt)
mac_key = hashlib.pbkdf2_hmac("sha512", enc_key, mac_salt, 2, dklen=KEY_SZ)

# IV is at bytes PAGE_SZ-RESERVE_SZ to PAGE_SZ-RESERVE_SZ+IV_SZ = 4016 to 4032
iv_start = PAGE_SZ - RESERVE_SZ
iv = page1[iv_start : iv_start + IV_SZ]
print(f'IV: {iv.hex()}, bytes {iv_start}-{iv_start+IV_SZ-1}')

# Encrypted data range for HMAC = SALT_SZ to iv_start = 16 to 4016
enc_data = page1[SALT_SZ : iv_start]
print(f'Enc data range: {SALT_SZ} to {iv_start}, {len(enc_data)} bytes')
print(f'Enc data first 32 bytes: {enc_data[:32].hex()}')

# HMAC stored at end
hmac_stored = page1[PAGE_SZ - HMAC_SZ : PAGE_SZ]
print(f'HMAC stored range: {PAGE_SZ-HMAC_SZ} to {PAGE_SZ-1}, {len(hmac_stored)} bytes')
print(f'HMAC stored: {hmac_stored.hex()}')

# Compute HMAC
hm = hmac_mod.new(mac_key, enc_data, hashlib.sha512)
hm.update(struct.pack('<I', 1))  # page number
comp = hm.digest()
print(f'HMAC computed: {comp.hex()}')
print(f'Match: {comp == hmac_stored}')

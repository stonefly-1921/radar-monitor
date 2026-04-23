"""
Try HMAC-SHA1 based key derivation (SQLITE_HASHER mode)
"""
import hashlib, struct, os
import hmac as hmac_mod
from Crypto.Cipher import AES

PAGE_SZ = 4096
SALT_SZ = 16
IV_SZ = 16
HMAC_SZ = 64
RESERVE_SZ = 80
SQLITE_HDR = b'SQLite format 3\x00'

enc_key = bytes.fromhex('ce21fdd6ae57c1f23cc4ce3e315ff857138773906331833f7f30a8e613dfab16')
salt = bytes.fromhex('0c60d940ad4890ed954927b20c051c4a')

db_path = r'C:\Users\15041\xwechat_files\wshjustin_3dff\db_storage\message\message_0.db'

with open(db_path, 'rb') as f:
    page1 = f.read(PAGE_SZ)

stored_hmac = page1[PAGE_SZ - HMAC_SZ : PAGE_SZ]
stored_iv = page1[PAGE_SZ - RESERVE_SZ : PAGE_SZ - RESERVE_SZ + IV_SZ]
salt_f = page1[:SALT_SZ]

# HMAC-SHA1 based MAC key derivation
for mac_iter in [1, 2, 64000, 256000]:
    mac_salt = bytes(b ^ 0x3a for b in salt)
    mac_key = hashlib.pbkdf2_hmac("sha1", enc_key, mac_salt, mac_iter, dklen=32)
    
    # Try HMAC-SHA512
    hmac_data = page1[SALT_SZ : PAGE_SZ - RESERVE_SZ + IV_SZ]
    hm = hmac_mod.new(mac_key, hmac_data, hashlib.sha512)
    hm.update(struct.pack('<I', 1))
    if hm.digest() == stored_hmac:
        print(f'HMAC-SHA512 match! mac_iter={mac_iter}')
    
    # Try HMAC-SHA1
    hm1 = hmac_mod.new(mac_key, hmac_data, 'sha1')
    hm1.update(struct.pack('<I', 1))
    if hm1.digest() == stored_hmac:
        print(f'HMAC-SHA1 match! mac_iter={mac_iter}')

# Try AES key derivations with HMAC-SHA1
print('\nTrying AES key derivations...')
enc_data = page1[SALT_SZ : PAGE_SZ - RESERVE_SZ]

for key_iter in [1, 2, 64000, 256000]:
    dk_aes = hashlib.pbkdf2_hmac("sha1", enc_key, salt, key_iter, dklen=64)
    aes_key = dk_aes[:32]
    
    for use_raw in [False, True]:
        k = enc_key if use_raw else aes_key
        cipher = AES.new(k, AES.MODE_CBC, stored_iv)
        dec = cipher.decrypt(enc_data)
        if dec[:16] == SQLITE_HDR:
            print(f'SQLite FOUND! iter={key_iter}, {"raw" if use_raw else "pbkdf2"}, key={k.hex()[:32]}')
        if dec[:4] == b'\x00\x00\x00\x00':
            print(f'All zeros! iter={key_iter}, {"raw" if use_raw else "pbkdf2"}')
        else:
            print(f'iter={key_iter}, {"raw" if use_raw else "pbkdf2"}, dec_start={dec[:16].hex()}')

# Also try: maybe enc_key itself is the cipher key, but with different data range
print('\nTrying raw enc_key with different enc ranges...')
for enc_start in [SALT_SZ, 0, 8]:
    for enc_end in [PAGE_SZ - RESERVE_SZ, 4016, PAGE_SZ - HMAC_SZ]:
        if enc_end <= enc_start:
            continue
        enc_r = page1[enc_start:enc_end]
        cipher = AES.new(enc_key, AES.MODE_CBC, stored_iv)
        dec = cipher.decrypt(enc_r)
        print(f'  raw enc [{enc_start}:{enc_end}] -> {dec[:16].hex()}')

print('\nDone.')

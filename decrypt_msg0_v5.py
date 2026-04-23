"""
Brute force: try different page layouts and key derivations to find the right decryption
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

print(f'Salt: {salt.hex()}')
print(f'IV: {stored_iv.hex()}')
print(f'Stored HMAC: {stored_hmac.hex()}')
print(f'Enc key: {enc_key.hex()}')

# Try different MAC key derivations
for mac_iter in [1, 2, 256000]:
    mac_salt = bytes(b ^ 0x3a for b in salt)
    mac_key = hashlib.pbkdf2_hmac("sha512", enc_key, mac_salt, mac_iter, dklen=32)
    
    # Try HMAC with different data ranges
    for hmac_data_end in [PAGE_SZ - RESERVE_SZ, PAGE_SZ - HMAC_SZ, 4016, 4032]:
        hmac_data = page1[SALT_SZ : hmac_data_end]
        hm = hmac_mod.new(mac_key, hmac_data, hashlib.sha512)
        hm.update(struct.pack('<I', 1))
        comp = hm.digest()
        if comp == stored_hmac:
            print(f'\nFound HMAC match! mac_iter={mac_iter}, hmac_data_end={hmac_data_end}')

# Try different AES key derivations
print('\nTrying different AES key derivations...')
for iterations in [1, 2, 256000]:
    dk = hashlib.pbkdf2_hmac("sha512", enc_key, salt, iterations, dklen=64)
    aes_key = dk[:32]
    
    # Try with raw enc_key
    for key_to_use in [enc_key, aes_key]:
        for enc_start in [SALT_SZ, 0, 16]:
            for enc_end in [PAGE_SZ - RESERVE_SZ, PAGE_SZ - HMAC_SZ, 4016, PAGE_SZ]:
                if enc_end <= enc_start:
                    continue
                iv_to_use = stored_iv
                cipher = AES.new(key_to_use, AES.MODE_CBC, iv_to_use)
                enc_data = page1[enc_start:enc_end]
                try:
                    dec = cipher.decrypt(enc_data)
                    if dec[:16] == SQLITE_HDR:
                        print(f'SQLITE FOUND! iter={iterations}, key={"pbkdf2" if key_to_use != enc_key else "raw"}, enc=({enc_start},{enc_end})')
                except:
                    pass

print('\nNow trying HMAC with IV included in data...')
for mac_iter in [1, 2, 256000]:
    mac_salt = bytes(b ^ 0x3a for b in salt)
    mac_key = hashlib.pbkdf2_hmac("sha512", enc_key, mac_salt, mac_iter, dklen=32)
    
    # HMAC = HMAC(mac_key, encrypted_data || IV || page_num)
    enc_data = page1[SALT_SZ : PAGE_SZ - RESERVE_SZ]
    hm_data = enc_data + stored_iv + struct.pack('<I', 1)
    hm = hmac_mod.new(mac_key, hm_data, hashlib.sha512)
    if hm.digest() == stored_hmac:
        print(f'HMAC match with IV||page! iter={mac_iter}')
        
    # Or HMAC(mac_key, IV || encrypted_data || page_num)
    hm_data2 = stored_iv + enc_data + struct.pack('<I', 1)
    hm2 = hmac_mod.new(mac_key, hm_data2, hashlib.sha512)
    if hm2.digest() == stored_hmac:
        print(f'HMAC match with IV||enc||page! iter={mac_iter}')

print('\nDone.')

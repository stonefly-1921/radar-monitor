"""
Try using the enc_key found IN the database file itself (bytes 16-47 of page 1)
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

# Key from memory scan
mem_key = bytes.fromhex('ce21fdd6ae57c1f23cc4ce3e315ff857138773906331833f7f30a8e613dfab16')

# Key from bytes 16-47 of message_0.db (the stored enc_key)
stored_enc_key = bytes.fromhex('6c8bf1f6a5097ba77845f8f7761d007f931d095868e736bec369b26e5ab23722')

db_path = r'C:\Users\15041\xwechat_files\wshjustin_3dff\db_storage\message\message_0.db'

with open(db_path, 'rb') as f:
    page1 = f.read(PAGE_SZ)

salt_f = page1[:SALT_SZ]
stored_iv = page1[PAGE_SZ - RESERVE_SZ : PAGE_SZ - RESERVE_SZ + IV_SZ]
stored_hmac = page1[PAGE_SZ - HMAC_SZ : PAGE_SZ]

# The stored_enc_key is 32 bytes from position 16-47
print(f'Salt: {salt_f.hex()}')
print(f'Memory key: {mem_key.hex()}')
print(f'Stored enc_key (from file bytes 16-47): {stored_enc_key.hex()}')
print(f'Stored IV: {stored_iv.hex()}')
print(f'Stored HMAC: {stored_hmac.hex()}')

# Try to verify HMAC with stored_enc_key
mac_salt = bytes(b ^ 0x3a for b in salt_f)
for mac_iter in [1, 2, 64000]:
    mac_key_mem = hashlib.pbkdf2_hmac("sha512", mem_key, mac_salt, mac_iter, dklen=32)
    mac_key_stored = hashlib.pbkdf2_hmac("sha512", stored_enc_key, mac_salt, mac_iter, dklen=32)
    
    hmac_data = page1[SALT_SZ : PAGE_SZ - RESERVE_SZ + IV_SZ]
    
    for hm_key, name in [(mac_key_mem, 'mem'), (mac_key_stored, 'stored')]:
        hm = hmac_mod.new(hm_key, hmac_data, hashlib.sha512)
        hm.update(struct.pack('<I', 1))
        if hm.digest() == stored_hmac:
            print(f'\nHMAC match! key={name}, mac_iter={mac_iter}')

# Try AES decryption with stored_enc_key
print('\nTrying AES with stored_enc_key...')
enc_data = page1[SALT_SZ : PAGE_SZ - RESERVE_SZ]
cipher = AES.new(stored_enc_key, AES.MODE_CBC, stored_iv)
dec = cipher.decrypt(enc_data)
print(f'stored_enc_key direct decrypt: {dec[:32].hex()}')
print(f'Is SQLite? {dec[:16] == SQLITE_HDR}')

# Try PBKDF2 derived from stored_enc_key
print('\nTrying PBKDF2 from stored_enc_key...')
for iterations in [1, 2, 64000, 256000]:
    dk = hashlib.pbkdf2_hmac("sha512", stored_enc_key, salt_f, iterations, dklen=64)
    aes_key = dk[:32]
    cipher = AES.new(aes_key, AES.MODE_CBC, stored_iv)
    dec = cipher.decrypt(enc_data)
    print(f'  PBKDF2 iter={iterations}: {dec[:32].hex()}, sqlite={dec[:16] == SQLITE_HDR}')

# Also try with mem_key
print('\nTrying PBKDF2 from mem_key...')
for iterations in [1, 2, 64000, 256000]:
    dk = hashlib.pbkdf2_hmac("sha512", mem_key, salt_f, iterations, dklen=64)
    aes_key = dk[:32]
    cipher = AES.new(aes_key, AES.MODE_CBC, stored_iv)
    dec = cipher.decrypt(enc_data)
    print(f'  PBKDF2 iter={iterations}: {dec[:32].hex()}, sqlite={dec[:16] == SQLITE_HDR}')

# Maybe the file bytes 16-47 IS the cipher key (used directly, no PBKDF2)
# And the memory key is something else (maybe HMAC key?)
print('\nTrying: memory_key as AES key, stored_enc_key as HMAC key...')
# Derive HMAC key from stored_enc_key
mac_salt2 = bytes(b ^ 0x3a for b in salt_f)
mac_key2 = hashlib.pbkdf2_hmac("sha512", stored_enc_key, mac_salt2, 2, dklen=32)
hm2 = hmac_mod.new(mac_key2, hmac_data, hashlib.sha512)
hm2.update(struct.pack('<I', 1))
print(f'HMAC with stored_enc_key: {hm2.digest().hex()}')
print(f'Stored HMAC: {stored_hmac.hex()}')
print(f'Match: {hm2.digest() == stored_hmac}')

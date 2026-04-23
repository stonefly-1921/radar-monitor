"""
Try direct AES decryption with raw enc_key (no PBKDF2)
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

db_path = r'C:\Users\15041\xwechat_files\wshjustin_3dff\db_storage\message\message_0.db'

with open(db_path, 'rb') as f:
    page1 = f.read(PAGE_SZ)

salt_f = page1[:SALT_SZ]
print('Salt:', salt_f.hex())
print('Enc key:', enc_key.hex())
print('Enc key len:', len(enc_key))

# Derive MAC key (from decrypt_db.py)
mac_salt = bytes(b ^ 0x3a for b in salt_f)
mac_key = hashlib.pbkdf2_hmac("sha512", enc_key, mac_salt, 2, dklen=32)
print('MAC key:', mac_key.hex())

# Verify HMAC
p1_hmac_data = page1[SALT_SZ : PAGE_SZ - RESERVE_SZ + IV_SZ]
p1_stored_hmac = page1[PAGE_SZ - HMAC_SZ : PAGE_SZ]
hm = hmac_mod.new(mac_key, p1_hmac_data, hashlib.sha512)
hm.update(struct.pack('<I', 1))
computed_hmac = hm.digest()
print('\nStored HMAC:', p1_stored_hmac.hex())
print('Computed HMAC:', computed_hmac.hex())
print('HMAC match:', computed_hmac == p1_stored_hmac)

# Try direct AES with raw enc_key (no PBKDF2)
iv = page1[PAGE_SZ - RESERVE_SZ : PAGE_SZ - RESERVE_SZ + IV_SZ]
encrypted = page1[SALT_SZ : PAGE_SZ - RESERVE_SZ]

print('\nTrying direct AES with raw enc_key...')
cipher = AES.new(enc_key, AES.MODE_CBC, iv)
decrypted = cipher.decrypt(encrypted)
print('Decrypted first 32 bytes:', decrypted[:32].hex())
print('Is SQLite?:', decrypted[:16] == SQLITE_HDR)

print('\nTrying with PBKDF2-derived key...')
dk = hashlib.pbkdf2_hmac("sha512", enc_key, salt_f, 256000, dklen=64)
aes_key_pbkdf = dk[:32]
cipher2 = AES.new(aes_key_pbkdf, AES.MODE_CBC, iv)
decrypted2 = cipher2.decrypt(encrypted)
print('Decrypted first 32 bytes:', decrypted2[:32].hex())
print('Is SQLite?:', decrypted2[:16] == SQLITE_HDR)

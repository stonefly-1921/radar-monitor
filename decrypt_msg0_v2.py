"""
Force decrypt message_0.db, bypassing HMAC check
"""
import hashlib, struct, os, json
import hmac as hmac_mod
from Crypto.Cipher import AES

PAGE_SZ = 4096
KEY_SZ = 32
SALT_SZ = 16
IV_SZ = 16
HMAC_SZ = 64
RESERVE_SZ = 80
SQLITE_HDR = b'SQLite format 3\x00'

enc_key = bytes.fromhex('ce21fdd6ae57c1f23cc4ce3e315ff857138773906331833f7f30a8e613dfab16')
salt = bytes.fromhex('0c60d940ad4890ed954927b20c051c4a')

db_path = r'C:\Users\15041\xwechat_files\wshjustin_3dff\db_storage\message\message_0.db'

def derive_mac_key(enc_key, salt):
    mac_salt = bytes(b ^ 0x3a for b in salt)
    return hashlib.pbkdf2_hmac("sha512", enc_key, mac_salt, 2, dklen=KEY_SZ)

# Verify HMAC
with open(db_path, 'rb') as f:
    page1 = f.read(PAGE_SZ)

salt_f = page1[:SALT_SZ]
mac_key = derive_mac_key(enc_key, salt_f)
p1_hmac_data = page1[SALT_SZ : PAGE_SZ - RESERVE_SZ + IV_SZ]
p1_stored_hmac = page1[PAGE_SZ - HMAC_SZ : PAGE_SZ]
hm = hmac_mod.new(mac_key, p1_hmac_data, hashlib.sha512)
hm.update(struct.pack('<I', 1))
print('HMAC match:', hm.digest() == p1_stored_hmac)

# Derive AES key
dk = hashlib.pbkdf2_hmac("sha512", enc_key, salt, 256000, dklen=64)
cipher_key = dk[:32]
print('Cipher key:', cipher_key.hex())

# Try decrypt page 1
iv = page1[PAGE_SZ - RESERVE_SZ : PAGE_SZ - RESERVE_SZ + IV_SZ]
encrypted = page_data = page1[SALT_SZ : PAGE_SZ - RESERVE_SZ]

cipher = AES.new(cipher_key, AES.MODE_CBC, iv)
decrypted = cipher.decrypt(encrypted)
print('Decrypted first 100 bytes:', decrypted[:100].hex())
print('Is SQLite?:', decrypted[:16] == SQLITE_HDR)
print('SQLite header:', decrypted[:16])

# Save full decrypted file (brute force, no HMAC)
out_path = r'C:\Users\15041\Desktop\wechat-decrypt\decrypted\message_0.db'
os.makedirs(os.path.dirname(out_path), exist_ok=True)

with open(db_path, 'rb') as fin, open(out_path, 'wb') as fout:
    pgno = 0
    while True:
        page_data = fin.read(PAGE_SZ)
        if len(page_data) < PAGE_SZ:
            break
        pgno += 1
        
        iv = page_data[PAGE_SZ - RESERVE_SZ : PAGE_SZ - RESERVE_SZ + IV_SZ]
        if pgno == 1:
            encrypted = page_data[SALT_SZ : PAGE_SZ - RESERVE_SZ]
            cipher = AES.new(cipher_key, AES.MODE_CBC, iv)
            dec = cipher.decrypt(encrypted)
            # For page 1: prepend salt (16 bytes) to make 4096
            page = bytearray(salt_f + dec)
            page += b'\x00' * (PAGE_SZ - len(page))
        else:
            encrypted = page_data[:PAGE_SZ - RESERVE_SZ]
            cipher = AES.new(cipher_key, AES.MODE_CBC, iv)
            dec = cipher.decrypt(encrypted)
            page = bytearray(dec + b'\x00' * RESERVE_SZ)
        
        fout.write(bytes(page))
        
        if pgno == 1 and dec[:16] == SQLITE_HDR:
            print(f'\nPage 1 decrypted OK! SQLite header confirmed.')

print(f'Done, wrote {pgno} pages')
print(f'Output: {out_path}')

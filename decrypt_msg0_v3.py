"""
Force decrypt message_0.db, bypassing HMAC check - clean version
"""
import hashlib, struct, os
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

# Derive AES key from enc_key + salt
dk = hashlib.pbkdf2_hmac("sha512", enc_key, salt, 256000, dklen=64)
cipher_key = dk[:32]
print('Cipher key:', cipher_key.hex())

# Decrypt page 1
with open(db_path, 'rb') as f:
    page1 = f.read(PAGE_SZ)

salt_f = page1[:SALT_SZ]
print('Salt in file:', salt_f.hex())
print('Salt matches:', salt_f == salt)

iv = page1[PAGE_SZ - RESERVE_SZ : PAGE_SZ - RESERVE_SZ + IV_SZ]
encrypted = page1[SALT_SZ : PAGE_SZ - RESERVE_SZ]  # bytes 16-4015, 4000 bytes

cipher = AES.new(cipher_key, AES.MODE_CBC, iv)
decrypted = cipher.decrypt(encrypted)

print('Decrypted first 32 bytes:', decrypted[:32].hex())
print('Is SQLite?:', decrypted[:16] == SQLITE_HDR)
print('SQLite header found at:', decrypted[:16])

# Write full decrypted file
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
            # Page 1: salt + encrypted + reserve; decrypted data starts with SQLite header
            enc = page_data[SALT_SZ : PAGE_SZ - RESERVE_SZ]
            cipher = AES.new(cipher_key, AES.MODE_CBC, iv)
            dec = cipher.decrypt(enc)
            # Output: salt + decrypted_data (salt is already consumed above)
            # But actually: the decrypted data IS the content, salt was for KDF only
            # The output SQLite file should have: SQLite header at byte 0
            # So we write: salt_placeholder + dec, then pad
            # Actually: the decrypted data already starts with SQLite header
            # So the file = salt + dec where salt=16 bytes prepended
            # No wait - SQLite files don't have salt at the start
            # The salt was used to derive the key, not part of the file content
            # The original DB file: salt + enc_data; after decrypt: enc_data becomes plaintext
            # The plaintext IS the SQLite content = 4000 bytes starting with SQLite header
            # So output = 4000 bytes = one page of SQLite
            # But page_size = 4096 in the file...
            # Hmm, let me just write the decrypted content as-is
            fout.write(dec)
        else:
            enc = page_data[:PAGE_SZ - RESERVE_SZ]
            cipher = AES.new(cipher_key, AES.MODE_CBC, iv)
            dec = cipher.decrypt(enc)
            # For non-page1: no salt prefix, just dec + reserve_pad
            # Actually standard SQLCipher for pages > 1: enc_data is full page except reserve
            dec_page = dec + b'\x00' * RESERVE_SZ
            fout.write(dec_page)
    
    print(f'Done, wrote {pgno} pages to {out_path}')

# Verify with SQLite
import sqlite3
try:
    conn = sqlite3.connect(out_path)
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    conn.close()
    print(f'SQLite tables: {[t[0] for t in tables][:10]}')
except Exception as e:
    print(f'SQLite error: {e}')
    # Check file size
    print(f'Output file size: {os.path.getsize(out_path)} bytes')

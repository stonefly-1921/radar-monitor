import sqlite3
import os

key_db = r'C:\Users\15041\xwechat_files\all_users\login\wshjustin\key_info.db'
print('key_info.db size:', os.path.getsize(key_db))

# Try to open as SQLite
try:
    conn = sqlite3.connect(key_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print('Tables:', [t[0] for t in tables])
    for t in tables:
        cursor.execute(f"SELECT * FROM {t[0]} LIMIT 5")
        rows = cursor.fetchall()
        print(f'Table {t[0]} rows:', rows)
    conn.close()
except Exception as e:
    print('Error:', e)

# Check raw header
with open(key_db, 'rb') as f:
    header = f.read(16)
    print('Header hex:', header.hex())

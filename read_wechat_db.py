import sqlite3
import os

# Try ChatMsg.db first
db_path = r'C:\Users\15041\Documents\WeChat Files\wshjustin\Msg\ChatMsg.db'
if os.path.exists(db_path):
    print(f'ChatMsg.db exists, size: {os.path.getsize(db_path)} bytes')
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f'Tables: {[t[0] for t in tables]}')
        conn.close()
    except Exception as e:
        print(f'Error: {e}')
else:
    print('ChatMsg.db not found')

# Check MSG0.db in Multi folder
msg_db = r'C:\Users\15041\Documents\WeChat Files\wshjustin\Msg\Multi\MSG0.db'
if os.path.exists(msg_db):
    print(f'MSG0.db exists, size: {os.path.getsize(msg_db)} bytes')
    try:
        conn = sqlite3.connect(msg_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f'Tables: {[t[0] for t in tables]}')
        conn.close()
    except Exception as e:
        print(f'Error: {e}')
else:
    print('MSG0.db not found')

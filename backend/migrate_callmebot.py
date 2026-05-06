import sqlite3

conn = sqlite3.connect('mindsense.db')
try:
    conn.execute('ALTER TABLE emergency_contacts ADD COLUMN callmebot_key VARCHAR DEFAULT ""')
    conn.commit()
    print("✅ Migration done: callmebot_key column added successfully!")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e):
        print("✅ Column already exists — no migration needed.")
    else:
        print(f"❌ Error: {e}")
finally:
    conn.close()

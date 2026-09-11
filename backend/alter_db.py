import sqlite3
import os

db_path = "/home/varun/Documents/maxwellMobAcc/backend/maxwell_acc.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("ALTER TABLE invoices ADD COLUMN delivery_challan_url VARCHAR(500)")
        conn.commit()
        print("Column added.")
    except Exception as e:
        print("Error:", e)
    conn.close()
else:
    print("DB not found.")

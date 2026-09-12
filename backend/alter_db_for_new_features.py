import sqlite3
import os

db_path = "/home/varun/Documents/maxwellMobAcc/backend/maxwell_acc.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("ALTER TABLE users ADD COLUMN is_superuser BOOLEAN DEFAULT 0")
        print("Column is_superuser added to users.")
    except Exception as e:
        print("Error altering users:", e)
        
    try:
        conn.execute("ALTER TABLE parties ADD COLUMN area VARCHAR(120)")
        print("Column area added to parties.")
    except Exception as e:
        print("Error altering parties (area):", e)
        
    try:
        conn.execute("ALTER TABLE parties ADD COLUMN reminder_date DATETIME")
        print("Column reminder_date added to parties.")
    except Exception as e:
        print("Error altering parties (reminder_date):", e)

    # Let's make existing users superusers for convenience as requested in the plan discussion
    try:
        conn.execute("UPDATE users SET is_superuser = 1")
        print("Set existing users as superusers.")
    except Exception as e:
        print("Error updating existing users:", e)

    conn.commit()
    conn.close()
else:
    print("DB not found.")

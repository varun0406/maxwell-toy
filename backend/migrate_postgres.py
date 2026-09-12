import os
import sys
from sqlalchemy import text

# Add current directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine

def migrate_postgres():
    print("Starting PostgreSQL migration...")
    
    with engine.connect() as conn:
        try:
            # 1. Add is_superuser to users
            conn.execute(text("ALTER TABLE users ADD COLUMN is_superuser BOOLEAN DEFAULT FALSE"))
            print("✓ Added 'is_superuser' column to 'users'")
        except Exception as e:
            print("  Skipped 'is_superuser':", str(e).split('\n')[0])

        try:
            # 2. Make existing users superusers
            conn.execute(text("UPDATE users SET is_superuser = TRUE"))
            print("✓ Set existing users as superusers")
        except Exception as e:
            print("  Error updating users:", str(e).split('\n')[0])

        try:
            # 3. Add area to parties
            conn.execute(text("ALTER TABLE parties ADD COLUMN area VARCHAR(120)"))
            print("✓ Added 'area' column to 'parties'")
        except Exception as e:
            print("  Skipped 'area':", str(e).split('\n')[0])
            
        try:
            # 4. Add reminder_date to parties
            conn.execute(text("ALTER TABLE parties ADD COLUMN reminder_date TIMESTAMP"))
            print("✓ Added 'reminder_date' column to 'parties'")
        except Exception as e:
            print("  Skipped 'reminder_date':", str(e).split('\n')[0])
            
        # Commit the transaction
        conn.commit()
        print("Migration complete!")

if __name__ == "__main__":
    migrate_postgres()

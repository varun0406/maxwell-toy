import os
import sys
from sqlalchemy import text

# Add current directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine

def migrate_postgres_phase2():
    print("Starting PostgreSQL migration for Phase 2 (Sales Returns)...")
    
    with engine.connect() as conn:
        try:
            # 1. Add voucher_id to payment_allocations
            conn.execute(text("""
                ALTER TABLE payment_allocations 
                ADD COLUMN voucher_id INTEGER;
            """))
            print("✓ Added 'voucher_id' column to 'payment_allocations'")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("✓ Column 'voucher_id' already exists.")
            else:
                print("  Error adding 'voucher_id':", str(e).split('\n')[0])

        try:
            # 2. Add foreign key constraint
            conn.execute(text("""
                ALTER TABLE payment_allocations 
                ADD CONSTRAINT fk_payment_allocations_vouchers 
                FOREIGN KEY (voucher_id) 
                REFERENCES vouchers (id) 
                ON DELETE CASCADE;
            """))
            print("✓ Added foreign key constraint for 'voucher_id'")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("✓ Foreign key constraint already exists.")
            else:
                print("  Error adding foreign key:", str(e).split('\n')[0])

        conn.commit()
        print("Phase 2 migration complete.")

if __name__ == "__main__":
    migrate_postgres_phase2()

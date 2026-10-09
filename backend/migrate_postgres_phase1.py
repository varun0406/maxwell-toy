import os
import sys
from sqlalchemy import text

# Add current directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine

def migrate_postgres_phase1():
    print("Starting PostgreSQL migration for Phase 1...")
    
    with engine.connect() as conn:
        try:
            # 1. Create accounts table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(50) UNIQUE,
                    name VARCHAR(200) NOT NULL,
                    account_type VARCHAR(50) NOT NULL,
                    parent_id INTEGER REFERENCES accounts(id),
                    is_party_control BOOLEAN DEFAULT FALSE,
                    is_system BOOLEAN DEFAULT FALSE,
                    active BOOLEAN DEFAULT TRUE
                );
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_accounts_code ON accounts(code);"))
            print("✓ Created 'accounts' table")
        except Exception as e:
            print("  Error creating 'accounts':", str(e).split('\n')[0])

        try:
            # 2. Create vouchers table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS vouchers (
                    id SERIAL PRIMARY KEY,
                    voucher_type VARCHAR(50) NOT NULL,
                    series VARCHAR(50),
                    number INTEGER,
                    voucher_date TIMESTAMP WITH TIME ZONE NOT NULL,
                    fy VARCHAR(20),
                    narration TEXT,
                    ref_voucher_id INTEGER REFERENCES vouchers(id),
                    status VARCHAR(50) NOT NULL DEFAULT 'POSTED',
                    created_by INTEGER NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    approved_by INTEGER,
                    posted_at TIMESTAMP WITH TIME ZONE,
                    reversed_by_voucher_id INTEGER REFERENCES vouchers(id),
                    source VARCHAR(50),
                    source_ref VARCHAR(200)
                );
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_vouchers_voucher_type ON vouchers(voucher_type);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_vouchers_voucher_date ON vouchers(voucher_date);"))
            print("✓ Created 'vouchers' table")
        except Exception as e:
            print("  Error creating 'vouchers':", str(e).split('\n')[0])

        try:
            # 3. Create voucher_lines table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS voucher_lines (
                    id SERIAL PRIMARY KEY,
                    voucher_id INTEGER NOT NULL REFERENCES vouchers(id) ON DELETE CASCADE,
                    account_id INTEGER NOT NULL REFERENCES accounts(id),
                    party_id INTEGER REFERENCES parties(id),
                    debit NUMERIC(14, 2) NOT NULL DEFAULT 0,
                    credit NUMERIC(14, 2) NOT NULL DEFAULT 0,
                    item_id INTEGER REFERENCES items(id),
                    qty NUMERIC(14, 3),
                    rate NUMERIC(14, 2),
                    tax_code VARCHAR(50),
                    line_narration TEXT
                );
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_voucher_lines_account ON voucher_lines(account_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_voucher_lines_party ON voucher_lines(party_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_voucher_lines_voucher ON voucher_lines(voucher_id);"))
            print("✓ Created 'voucher_lines' table")
        except Exception as e:
            print("  Error creating 'voucher_lines':", str(e).split('\n')[0])

        # Commit the transaction
        conn.commit()
        print("Migration complete!")

if __name__ == "__main__":
    migrate_postgres_phase1()

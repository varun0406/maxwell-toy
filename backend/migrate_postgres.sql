-- Run these commands on your PostgreSQL server to add the new tables and columns

-- 1. Create AccountMasters table
CREATE TABLE IF NOT EXISTS account_masters (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) UNIQUE NOT NULL,
    group_name VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_account_masters_name ON account_masters(name);

-- 2. Add account_id to journal_entries (if not exists)
DO $$ BEGIN
    ALTER TABLE journal_entries ADD COLUMN account_id INTEGER REFERENCES account_masters(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_column THEN NULL;
END $$;
CREATE INDEX IF NOT EXISTS ix_journal_entries_account_id ON journal_entries(account_id);

-- 3. Make payment_allocations.payment_id nullable (if not already)
ALTER TABLE payment_allocations ALTER COLUMN payment_id DROP NOT NULL;

-- 4. Add journal_id to payment_allocations (if not exists)
DO $$ BEGIN
    ALTER TABLE payment_allocations ADD COLUMN journal_id INTEGER REFERENCES journal_entries(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_column THEN NULL;
END $$;

-- 5. Add discount_amount to payments (if not exists)
DO $$ BEGIN
    ALTER TABLE payments ADD COLUMN discount_amount NUMERIC(12, 2) NOT NULL DEFAULT 0;
EXCEPTION
    WHEN duplicate_column THEN NULL;
END $$;

-- Done! Now you can run: python3 wipe_transactions.py && python3 import_transactions.py ...

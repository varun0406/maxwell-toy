-- Migration for Phase 1: Core Double-Entry Accounting
-- Run these commands on your PostgreSQL server to add the new tables

-- 1. Create Accounts table
CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE,
    name VARCHAR(200) NOT NULL,
    account_type VARCHAR(50) NOT NULL, -- ASSET, LIABILITY, EQUITY, INCOME, EXPENSE
    parent_id INTEGER REFERENCES accounts(id),
    is_party_control BOOLEAN DEFAULT FALSE,
    is_system BOOLEAN DEFAULT FALSE,
    active BOOLEAN DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS ix_accounts_code ON accounts(code);

-- 2. Create Vouchers table
CREATE TABLE IF NOT EXISTS vouchers (
    id SERIAL PRIMARY KEY,
    voucher_type VARCHAR(50) NOT NULL, -- SALE, RECEIPT, PURCHASE, PAYMENT, CREDIT_NOTE, DEBIT_NOTE, JOURNAL, CONTRA
    series VARCHAR(50),
    number INTEGER,
    voucher_date TIMESTAMP WITH TIME ZONE NOT NULL,
    fy VARCHAR(20),
    narration TEXT,
    ref_voucher_id INTEGER REFERENCES vouchers(id),
    status VARCHAR(50) NOT NULL DEFAULT 'POSTED', -- DRAFT, POSTED, CANCELLED, REVERSED
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    approved_by INTEGER,
    posted_at TIMESTAMP WITH TIME ZONE,
    reversed_by_voucher_id INTEGER REFERENCES vouchers(id),
    source VARCHAR(50),
    source_ref VARCHAR(200)
);
CREATE INDEX IF NOT EXISTS ix_vouchers_voucher_type ON vouchers(voucher_type);
CREATE INDEX IF NOT EXISTS ix_vouchers_voucher_date ON vouchers(voucher_date);

-- 3. Create Voucher Lines table
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
CREATE INDEX IF NOT EXISTS ix_voucher_lines_account ON voucher_lines(account_id);
CREATE INDEX IF NOT EXISTS ix_voucher_lines_party ON voucher_lines(party_id);
CREATE INDEX IF NOT EXISTS ix_voucher_lines_voucher ON voucher_lines(voucher_id);

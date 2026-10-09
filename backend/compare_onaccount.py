import csv
import sys
sys.path.append("/home/varun/Documents/maxwellMobAcc/backend")
from app.database import SessionLocal
from sqlalchemy import text
from decimal import Decimal

db = SessionLocal()

expected_balances = {}
with open("/home/varun/Documents/maxwellMobAcc/onaccount.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        account = row["Account"].strip()
        payable = row["Amt. Payable"].replace(",", "").strip()
        receivable = row["Amt. Receivable"].replace(",", "").strip()
        
        expected_payable = Decimal(payable) if payable else Decimal('0')
        expected_receivable = Decimal(receivable) if receivable else Decimal('0')
        
        expected_balances[account] = expected_payable - expected_receivable

print(f"{'Account':<35} | {'Expected':>15} | {'Our System':>15} | {'Diff':>15}")
print("-" * 88)

total_diff = Decimal('0')
total_expected = Decimal('0')
total_ours = Decimal('0')

for account, expected in expected_balances.items():
    if not account: continue
    row = db.execute(text("""
        WITH p_agg AS (
            SELECT p.id as party_id, 
                   SUM(pay.unallocated) AS unallocated_payments
            FROM parties p
            JOIN payments pay ON pay.party_id = p.id
            WHERE COALESCE(pay.is_deleted, false) = false AND p.name LIKE :name
            GROUP BY p.id
        ),
        j_unalloc AS (
            SELECT p.id as party_id, 
                   SUM(ABS(j.amount) - COALESCE((SELECT SUM(allocated_amount) FROM payment_allocations WHERE journal_id = j.id), 0)) AS unallocated_journals
            FROM parties p
            JOIN journal_entries j ON j.party_id = p.id
            WHERE j.amount < 0 AND COALESCE(j.is_deleted, false) = false AND p.name LIKE :name
            GROUP BY p.id
        )
        SELECT
            p.id,
            COALESCE(p_agg.unallocated_payments, 0) + COALESCE(j_unalloc.unallocated_journals, 0) AS unallocated_payments
        FROM parties p
        LEFT JOIN p_agg ON p_agg.party_id = p.id
        LEFT JOIN j_unalloc ON j_unalloc.party_id = p.id
        WHERE p.name LIKE :name
    """), {"name": f"%{account}%"}).fetchone()

    our_val = Decimal(str(row[1])) if row and row[1] is not None else Decimal('0')
    diff = expected - our_val
    total_diff += diff
    total_expected += expected
    total_ours += our_val
    
    if abs(diff) > 0.01:
        print(f"{account:<35} | {expected:>15.2f} | {our_val:>15.2f} | {diff:>15.2f}")

print("-" * 88)
print(f"{'TOTALS':<35} | {total_expected:>15.2f} | {total_ours:>15.2f} | {total_diff:>15.2f}")

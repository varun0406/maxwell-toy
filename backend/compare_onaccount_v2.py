import csv
import sys
sys.path.append("/home/varun/Documents/maxwellMobAcc/backend")
from app.database import SessionLocal
from sqlalchemy import text
from decimal import Decimal

db = SessionLocal()

print(f"{'Account':<35} | {'Expected Payable':>18} | {'Our Payable':>15} | {'Diff Payable':>15} | {'Exp Receiv':>15} | {'Our Receiv':>15} | {'Diff Receiv':>15}")
print("-" * 135)

total_diff_payable = Decimal('0')
total_diff_receivable = Decimal('0')

with open("/home/varun/Documents/maxwellMobAcc/onaccount.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        account = row["Account"].strip()
        payable = row["Amt. Payable"].replace(",", "").strip()
        receivable = row["Amt. Receivable"].replace(",", "").strip()
        
        expected_payable = Decimal(payable) if payable else Decimal('0')
        expected_receivable = Decimal(receivable) if receivable else Decimal('0')
        
        # Our Payable = unallocated payments
        our_p_row = db.execute(text("""
            WITH p_agg AS (
                SELECT p.id as party_id, SUM(pay.unallocated) AS unallocated_payments
                FROM parties p JOIN payments pay ON pay.party_id = p.id
                WHERE COALESCE(pay.is_deleted, false) = false AND p.name ILIKE :name GROUP BY p.id
            ), j_unalloc AS (
                SELECT p.id as party_id, SUM(ABS(j.amount) - COALESCE((SELECT SUM(allocated_amount) FROM payment_allocations WHERE journal_id = j.id), 0)) AS unallocated_journals
                FROM parties p JOIN journal_entries j ON j.party_id = p.id
                WHERE j.amount < 0 AND COALESCE(j.is_deleted, false) = false AND p.name ILIKE :name GROUP BY p.id
            )
            SELECT COALESCE(p_agg.unallocated_payments, 0) + COALESCE(j_unalloc.unallocated_journals, 0) AS unallocated_payments
            FROM parties p
            LEFT JOIN p_agg ON p_agg.party_id = p.id LEFT JOIN j_unalloc ON j_unalloc.party_id = p.id
            WHERE p.name ILIKE :name
        """), {"name": f"%{account}%"}).fetchone()
        our_payable = Decimal(str(our_p_row[0])) if our_p_row and our_p_row[0] is not None else Decimal('0')
        
        # Our Receivable = unpaid invoices
        our_r_row = db.execute(text("""
            SELECT SUM(i.balance_due)
            FROM parties p JOIN invoices i ON i.party_id = p.id
            WHERE COALESCE(i.is_deleted, false) = false AND p.name ILIKE :name
        """), {"name": f"%{account}%"}).fetchone()
        our_receivable = Decimal(str(our_r_row[0])) if our_r_row and our_r_row[0] is not None else Decimal('0')
        
        diff_p = expected_payable - our_payable
        diff_r = expected_receivable - our_receivable
        
        total_diff_payable += diff_p
        total_diff_receivable += diff_r
        
        if abs(diff_p) > 0.01 or abs(diff_r) > 0.01:
            print(f"{account:<35} | {expected_payable:>18.2f} | {our_payable:>15.2f} | {diff_p:>15.2f} | {expected_receivable:>15.2f} | {our_receivable:>15.2f} | {diff_r:>15.2f}")

print("-" * 135)
print(f"TOTAL DIFFERENCES: Payable Diff = {total_diff_payable:.2f}, Receivable Diff = {total_diff_receivable:.2f}")


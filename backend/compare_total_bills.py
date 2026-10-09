import csv
import sys
sys.path.append("/home/varun/Documents/maxwellMobAcc/backend")
from app.database import SessionLocal
from sqlalchemy import text
from decimal import Decimal

db = SessionLocal()

print(f"{'Account':<35} | {'Exp Pending':>15} | {'Our Pending':>15} | {'Diff':>15}")
print("-" * 88)

total_diff = Decimal('0')
total_expected = Decimal('0')
total_ours = Decimal('0')

with open("/home/varun/Documents/maxwellMobAcc/totalbilloutstanding.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        account = row["Account"].strip()
        if not account: continue
        pending = row["Pending Amt."].replace(",", "").strip()
        expected_pending = Decimal(pending) if pending else Decimal('0')
        
        our_row = db.execute(text("""
            SELECT SUM(i.balance_due)
            FROM parties p
            JOIN invoices i ON i.party_id = p.id
            WHERE COALESCE(i.is_deleted, false) = false AND p.name LIKE :name
        """), {"name": f"%{account}%"}).fetchone()
        
        our_val = Decimal(str(our_row[0])) if our_row and our_row[0] is not None else Decimal('0')
        
        diff = expected_pending - our_val
        total_expected += expected_pending
        total_ours += our_val
        total_diff += diff
        
        if abs(diff) > 0.01:
            print(f"{account:<35} | {expected_pending:>15.2f} | {our_val:>15.2f} | {diff:>15.2f}")

print("-" * 88)
print(f"TOTALS: Exp {total_expected:.2f} | Our {total_ours:.2f} | Diff {total_diff:.2f}")


import sys
import json
sys.path.append("/home/varun/Documents/maxwellMobAcc/backend")
from app.database import SessionLocal
from app.models import Party, Payment, Invoice
db = SessionLocal()
party = db.query(Party).filter(Party.name.ilike('%TARUN%ASHOK%KUMAR%')).first()
print(f"Party: {party.name}")
print("--- Unallocated Payments ---")
for pmt in db.query(Payment).filter_by(party_id=party.id).all():
    if pmt.unallocated > 0:
        print(f"Pmt {pmt.id} on {pmt.payment_date}: Amt {pmt.amount}, Unalloc {pmt.unallocated}")

print("--- Unpaid Invoices ---")
for inv in db.query(Invoice).filter_by(party_id=party.id).all():
    if inv.balance_due > 0:
        print(f"Inv {inv.invoice_number} on {inv.invoice_date}: Amt {inv.amount}, Due {inv.balance_due}")


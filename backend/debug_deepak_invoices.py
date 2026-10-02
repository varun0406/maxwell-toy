import sys
import json
sys.path.append("/home/varun/Documents/maxwellMobAcc/backend")
from app.database import SessionLocal
from app.models import Party

db = SessionLocal()
party = db.query(Party).filter(Party.name.ilike('%Deepakbhai%Bhavnagar%')).first()
if not party:
    print("Party not found")
    sys.exit(0)

print(f"Party: {party.name} (ID: {party.id})")
print("\n--- Invoices ---")
for inv in party.invoices:
    print(f"Inv {inv.invoice_number} on {inv.invoice_date.date()}: Amount {inv.amount}, Due {inv.balance_due}, Paid {inv.is_paid}")

# Read import report
with open('/home/varun/Documents/maxwellMobAcc/backend/import-report.json') as f:
    rep = json.load(f)

print("\n--- Unresolved Allocations (Receipts) ---")
for src in rep['sources']:
    for alloc in src.get('unresolved_allocations', []):
        if alloc['type'] == 'Receipt' and alloc['date'].endswith('2025') or alloc['date'].endswith('2026'):
            print(alloc)


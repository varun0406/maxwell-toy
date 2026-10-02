import sys
sys.path.append("/home/varun/Documents/maxwellMobAcc/backend")
from app.database import SessionLocal
from app.models import Party, Invoice, Payment, JournalEntry, PaymentAllocation

db = SessionLocal()
party = db.query(Party).filter(Party.name.ilike('%Deepakbhai%Bhavnagar%')).first()
if not party:
    print("Party not found")
    sys.exit(0)

print(f"Party: {party.name} (ID: {party.id})")
print(f"BUSY Closing Bal: {party.busy_closing_balance}")

print("\n--- Invoices ---")
for inv in party.invoices:
    print(f"Inv {inv.invoice_number} on {inv.invoice_date.date()}: Amount {inv.amount}, Due {inv.balance_due}, Paid {inv.is_paid}")

print("\n--- Payments ---")
for pmt in party.payments:
    print(f"Pmt {pmt.id} on {pmt.payment_date.date()}: Amount {pmt.amount}, Discount {pmt.discount_amount}, Unallocated {pmt.unallocated}, Mode: {pmt.mode}")
    for alloc in pmt.allocations:
        print(f"  -> Alloc: {alloc.allocated_amount} to Inv {alloc.invoice_number}")

print("\n--- Journals ---")
for j in party.journal_entries:
    print(f"Jnl {j.id} on {j.entry_date.date()}: Amount {j.amount}, Contra {j.contra_amount}, Desc {j.description}")
    for alloc in j.allocations:
        print(f"  -> Alloc: {alloc.allocated_amount} to Inv {alloc.invoice_number}")


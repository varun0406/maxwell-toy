import sys
sys.path.append("/home/varun/Documents/maxwellMobAcc/backend")
from app.database import SessionLocal
from app.models import Party, Invoice, Payment, JournalEntry, PaymentAllocation
from decimal import Decimal

db = SessionLocal()
party = db.query(Party).filter(Party.name.ilike('%Deepakbhai%Bhavnagar%')).first()
if not party:
    print("Party not found")
    sys.exit(0)

# Calculate Total Bill Outstanding (sum of inv.balance_due)
invoices = db.query(Invoice).filter_by(party_id=party.id, is_deleted=False).all()
total_bill_outstanding = sum(inv.balance_due for inv in invoices)
total_invoiced = sum(inv.amount for inv in invoices)

# Calculate Unallocated Payments (sum of pmt.unallocated)
payments = db.query(Payment).filter_by(party_id=party.id, is_deleted=False).all()
total_unallocated = sum(pmt.unallocated for pmt in payments)
total_payments = sum(pmt.amount for pmt in payments)

# Calculate Journals (sum of journal.amount)
journals = db.query(JournalEntry).filter_by(party_id=party.id).all()
total_journal = sum(j.amount for j in journals)

# What is Net Outstanding in our DB?
# Net = Total Invoiced - Total Payments + Total Journal
net_outstanding = total_invoiced - total_payments + total_journal
constructed_net = total_bill_outstanding - total_unallocated

print(f"Party: {party.name} (ID: {party.id})")
print(f"BUSY Closing Bal (Master): {party.busy_closing_balance}")
print("-" * 40)
print(f"Total Invoiced (Sum of Sales): {total_invoiced}")
print(f"Total Payments (Receipts/Payments): {total_payments}")
print(f"Total Journal Adjustments: {total_journal}")
print("-" * 40)
print(f"Total Bill Outstanding (Unpaid Invoices): {total_bill_outstanding}")
print(f"On Account Balance (Unallocated Pmt): {total_unallocated}")
print("-" * 40)
print(f"Net Outstanding (Formula 1): {net_outstanding}")
print(f"Net Outstanding (Formula 2): {constructed_net}")


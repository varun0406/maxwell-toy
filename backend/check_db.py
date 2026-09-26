import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.models import Party, Invoice, InvoiceItem, Payment, JournalEntry
from app.database import SessionLocal

session = SessionLocal()

print("--- INVOICES ---")
inv = session.query(Invoice).first()
if inv:
    print(f"Invoice: {inv.invoice_number}, Date: {inv.invoice_date}, Amt: {inv.amount}, Bal: {inv.balance_due}")
    for item in inv.items:
        print(f"  Item: {item.item_name}, Meter: {item.meter}, Rate: {item.rate}, Total: {item.total}")
else:
    print("No invoices found")

print("\n--- PAYMENTS ---")
pmt = session.query(Payment).first()
if pmt:
    print(f"Payment: {pmt.id}, Date: {pmt.payment_date}, Amt: {pmt.amount}, Mode: {pmt.mode}")
else:
    print("No payments found")

print("\n--- JOURNAL ENTRIES ---")
jes = session.query(JournalEntry).all()
print(f"Total Journal Entries: {len(jes)}")
if jes:
    je = jes[0]
    print(f"Sample JE: ID={je.id}, Amt={je.amount}, Desc={je.description}")

session.close()

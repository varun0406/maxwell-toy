import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.models import Invoice, InvoiceItem, Payment, PaymentAllocation, Party, JournalEntry, AccountMaster
from app.database import SessionLocal

def wipe_transactions():
    session = SessionLocal()
    print("Deleting PaymentAllocations...")
    session.query(PaymentAllocation).delete()
    print("Deleting Payments...")
    session.query(Payment).delete()
    print("Deleting InvoiceItems...")
    session.query(InvoiceItem).delete()
    print("Deleting JournalEntries...")
    session.query(JournalEntry).delete()
    print("Deleting Invoices...")
    session.query(Invoice).delete()
    print("Deleting AccountMasters...")
    session.query(AccountMaster).delete()
    print("Deleting Parties...")
    session.query(Party).delete()
    session.commit()
    print("Wipe complete.")

if __name__ == "__main__":
    wipe_transactions()

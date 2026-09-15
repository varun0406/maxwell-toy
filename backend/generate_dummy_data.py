import sys
import os
from datetime import datetime, timezone, timedelta
import random
from decimal import Decimal

# Add backend directory to sys path so we can import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import User, Party, Invoice, Payment, JournalEntry
from app.auth import hash_password

def run():
    db = SessionLocal()
    
    try:
        # 1. Ensure user exists
        user = db.query(User).filter(User.username == "admin").first()
        if not user:
            user = User(
                username="admin", 
                email="admin@test.com", 
                hashed_password=hash_password("admin"),
                is_superuser=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
        print(f"Using user_id: {user.id}")
        
        print("Generating 20,000 Parties...")
        parties_data = []
        for i in range(20000):
            parties_data.append({
                "name": f"Dummy Party {random.randint(100000, 999999)}",
                "phone": f"555-{random.randint(1000, 9999)}",
                "created_by": user.id,
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            })
        
        db.bulk_insert_mappings(Party, parties_data)
        db.commit()
        print("Parties inserted.")
        
        # Get all party ids to map invoices/payments
        party_ids = [p.id for p in db.query(Party.id).all()]
        
        print("Generating 100,000 Invoices...")
        invoices_data = []
        now = datetime.now(timezone.utc)
        for i in range(100000):
            pid = random.choice(party_ids)
            amt = Decimal(str(random.randint(100, 10000)))
            invoices_data.append({
                "invoice_number": f"INV-DUMMY-{i}-{random.randint(1000, 9999)}",
                "party_id": pid,
                "created_by": user.id,
                "amount": amt,
                "balance_due": amt,
                "invoice_date": now - timedelta(days=random.randint(0, 365)),
                "due_date": now - timedelta(days=random.randint(-30, 335)),
                "is_paid": False,
                "is_deleted": False,
                "created_at": now,
                "updated_at": now
            })
            
            if len(invoices_data) >= 10000:
                db.bulk_insert_mappings(Invoice, invoices_data)
                invoices_data = []
                
        if invoices_data:
            db.bulk_insert_mappings(Invoice, invoices_data)
        db.commit()
        print("Invoices inserted.")
        
        print("Generating 50,000 Payments...")
        payments_data = []
        for i in range(50000):
            pid = random.choice(party_ids)
            amt = Decimal(str(random.randint(10, 5000)))
            payments_data.append({
                "party_id": pid,
                "created_by": user.id,
                "amount": amt,
                "unallocated": amt,
                "payment_date": now - timedelta(days=random.randint(0, 365)),
                "is_deleted": False,
                "created_at": now,
            })
            if len(payments_data) >= 10000:
                db.bulk_insert_mappings(Payment, payments_data)
                payments_data = []
                
        if payments_data:
            db.bulk_insert_mappings(Payment, payments_data)
        db.commit()
        print("Payments inserted.")
        
        print("Generating 30,000 Journal Entries...")
        journals_data = []
        for i in range(30000):
            pid = random.choice(party_ids)
            amt = Decimal(str(random.randint(-500, 500)))
            journals_data.append({
                "party_id": pid,
                "created_by": user.id,
                "amount": amt,
                "entry_date": now - timedelta(days=random.randint(0, 365)),
                "is_deleted": False,
                "created_at": now,
            })
            if len(journals_data) >= 10000:
                db.bulk_insert_mappings(JournalEntry, journals_data)
                journals_data = []
                
        if journals_data:
            db.bulk_insert_mappings(JournalEntry, journals_data)
        db.commit()
        
        print("Dummy data generation complete. Total records ~200,000.")

    except Exception as e:
        print(f"Error occurred: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run()

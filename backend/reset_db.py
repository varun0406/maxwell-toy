import sys
import os

# Append the current directory to sys.path so we can import from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from sqlalchemy import text

def reset_database():
    print("WARNING: This will delete ALL transactional data (invoices, payments, parties, etc.)")
    print("Users and refresh tokens will be preserved.")
    confirm = input("Type 'YES' to confirm: ")
    
    if confirm != 'YES':
        print("Aborted.")
        return

    with engine.begin() as conn:
        print("Disabling foreign key constraints temporarily...")
        # Since PostgreSQL supports CASCADE on TRUNCATE, we don't strictly need to disable triggers,
        # but TRUNCATE ... CASCADE is sufficient.
        
        tables_to_truncate = [
            "parties",
            "invoices",
            "invoice_items",
            "payments",
            "payment_allocations",
            "journal_entries",
            "address_book"
        ]
        
        print(f"Truncating tables: {', '.join(tables_to_truncate)}")
        # In PostgreSQL, TRUNCATE with CASCADE automatically truncates referencing tables
        # and RESTART IDENTITY resets auto-incrementing sequences.
        sql = f"TRUNCATE TABLE {', '.join(tables_to_truncate)} RESTART IDENTITY CASCADE"
        conn.execute(text(sql))
        
        print("Database successfully reset. Only users are preserved.")

if __name__ == "__main__":
    reset_database()

import argparse
import sys
import os

# Append the current directory to sys.path so we can import from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from sqlalchemy import text

TABLES = (
    "payment_allocations",
    "payments",
    "invoice_items",
    "invoices",
    "journal_entries",
    "parties",
    "address_book",
)


def reset_database(confirm=False, dry_run=False):
    print("WARNING: this deletes all invoices, payments, allocations, journals, parties, and addresses.")
    print("Users, refresh tokens, and item master records are preserved.")
    if dry_run:
        print("Dry run: would clear: " + ", ".join(TABLES))
        return
    if not confirm:
        typed = input("Type RESET-MAXWELL to confirm: ").strip()
        if typed != "RESET-MAXWELL":
            print("Aborted.")
            return

    with engine.begin() as conn:
        print(f"Deleting rows from: {', '.join(TABLES)}")
        for table in TABLES:
            conn.execute(text(f"DELETE FROM {table}"))
        print("Database successfully reset. Only users are preserved.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Safely clear imported accounting data.")
    parser.add_argument("--yes", action="store_true", help="Confirm reset non-interactively.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted.")
    args = parser.parse_args()
    reset_database(confirm=args.yes, dry_run=args.dry_run)

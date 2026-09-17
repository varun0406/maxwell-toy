"""
Performance Optimization Migration — Maxwell Accounting
=======================================================

Adds all indexes required for fast queries on 2–4 lakh records.
Safe to run on an existing production database: every statement is
wrapped in a try/except so it skips things that already exist.

Run with:
    python optimize_indexes.py

Make sure DATABASE_URL is set in your .env (or environment) before running.
"""

import os
import sys
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine  # reads DATABASE_URL from .env


# ---------------------------------------------------------------------------
# Index definitions
# (name, table, columns, extras)
# ---------------------------------------------------------------------------

INDEXES = [
    # parties
    ("ix_parties_name",             "parties",          "name"),
    ("ix_parties_is_active_name",   "parties",          "is_active, name"),

    # invoices — most critical for analytics aggregations
    ("ix_invoices_party_deleted",           "invoices",  "party_id, is_deleted"),
    ("ix_invoices_deleted_paid",            "invoices",  "is_deleted, is_paid"),
    ("ix_invoices_invoice_date",            "invoices",  "invoice_date"),
    ("ix_invoices_due_date",                "invoices",  "due_date"),
    ("ix_invoices_party_unpaid_balance",    "invoices",  "party_id, is_deleted, is_paid, balance_due"),

    # invoice_items
    ("ix_invoice_items_invoice_id",  "invoice_items",  "invoice_id"),

    # payments
    ("ix_payments_party_deleted",   "payments",  "party_id, is_deleted"),
    ("ix_payments_payment_date",    "payments",  "payment_date"),

    # payment_allocations — critical for delete-payment and delete-invoice loops
    ("ix_payment_allocations_payment_id",  "payment_allocations",  "payment_id"),
    ("ix_payment_allocations_invoice_id",  "payment_allocations",  "invoice_id"),

    # journal_entries
    ("ix_journal_entries_party_deleted",  "journal_entries",  "party_id, is_deleted"),
]


def run_migration():
    print("=" * 60)
    print("Maxwell Accounting — Performance Index Migration")
    print("=" * 60)

    created = 0
    skipped = 0
    errors = 0

    with engine.connect() as conn:
        for index_name, table, columns in INDEXES:
            try:
                sql = f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name} ON {table} ({columns})"
                conn.execute(text(sql))
                # CONCURRENTLY cannot run inside a transaction block in older PG;
                # autocommit is needed. Let's commit between each index.
                conn.execute(text("COMMIT"))
                print(f"  ✓  {index_name}  ON  {table}({columns})")
                created += 1
            except Exception as e:
                err_line = str(e).split("\n")[0]
                if "already exists" in err_line.lower():
                    print(f"  —  {index_name}  (already exists, skipped)")
                    skipped += 1
                else:
                    print(f"  ✗  {index_name}  ERROR: {err_line}")
                    errors += 1
                # Rollback any aborted transaction before continuing
                try:
                    conn.execute(text("ROLLBACK"))
                except Exception:
                    pass

    print()
    print(f"Done. Created: {created}  |  Skipped: {skipped}  |  Errors: {errors}")

    if errors:
        print("\n⚠  Some indexes failed to create — check errors above.")
        sys.exit(1)
    else:
        print("\n✅  All indexes are in place. Backend is now optimized for large datasets.")


if __name__ == "__main__":
    run_migration()

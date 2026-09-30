import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

session = SessionLocal()
res = session.execute(text("""
    SELECT 
        (SELECT SUM(amount) FROM invoices WHERE party_id = (SELECT id FROM parties WHERE name = 'RAJA BHAI(SURAT)') AND is_deleted = false) as sales,
        (SELECT SUM(amount) FROM payments WHERE party_id = (SELECT id FROM parties WHERE name = 'RAJA BHAI(SURAT)') AND is_deleted = false) as payments,
        (SELECT SUM(amount) FROM journal_entries WHERE party_id = (SELECT id FROM parties WHERE name = 'RAJA BHAI(SURAT)') AND is_deleted = false) as journals
""")).fetchone()

print("DB Totals:")
print(f"Sales (+): {res.sales}")
print(f"Payments (-): {res.payments}")
print(f"Journals (+/-): {res.journals}")
print(f"Total: {float(res.sales or 0) + float(res.journals or 0) - float(res.payments or 0)}")

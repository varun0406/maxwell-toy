import sys
import json
sys.path.append("/home/varun/Documents/maxwellMobAcc/backend")
from app.database import SessionLocal
from app.models import Party
from sqlalchemy import text

db = SessionLocal()
party_id = db.query(Party).filter(Party.name.ilike('%Deepakbhai%Bhavnagar%')).first().id

row = db.execute(text("""
    WITH p_agg AS (
        SELECT party_id, 
               SUM(amount) AS total_paid,
               SUM(unallocated) AS unallocated_payments
        FROM payments WHERE COALESCE(is_deleted, false) = false AND party_id = :party_id GROUP BY party_id
    ),
    j_unalloc AS (
        SELECT party_id, 
               SUM(ABS(amount) - COALESCE((SELECT SUM(allocated_amount) FROM payment_allocations WHERE journal_id = j.id), 0)) AS unallocated_journals
        FROM journal_entries j
        WHERE amount < 0 AND COALESCE(is_deleted, false) = false AND party_id = :party_id GROUP BY party_id
    )
    SELECT
        COALESCE(p_agg.unallocated_payments, 0) + COALESCE(j_unalloc.unallocated_journals, 0) AS unallocated_payments
    FROM parties p
    LEFT JOIN p_agg ON p_agg.party_id = p.id
    LEFT JOIN j_unalloc ON j_unalloc.party_id = p.id
    WHERE p.id = :party_id
"""), {"party_id": party_id}).fetchone()

print("Unallocated Payments from SQL logic:", row[0])


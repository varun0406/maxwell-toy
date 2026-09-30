import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

session = SessionLocal()

# Simpler query - avoid self-join cartesian product
result = session.execute(text("""
    WITH bills AS (
        SELECT party_id, SUM(balance_due) AS bills_out
        FROM invoices WHERE is_deleted = false GROUP BY party_id
    ),
    inv_sum AS (
        SELECT party_id, SUM(amount) AS total_inv
        FROM invoices WHERE is_deleted = false GROUP BY party_id
    ),
    jrn_sum AS (
        SELECT party_id, SUM(amount) AS total_jrn
        FROM journal_entries WHERE is_deleted = false GROUP BY party_id
    ),
    pay_sum AS (
        SELECT party_id, SUM(amount) AS total_pay
        FROM payments WHERE is_deleted = false GROUP BY party_id
    )
    SELECT
        pt.name,
        COALESCE(b.bills_out, 0)                                                    AS bills_outstanding,
        COALESCE(i.total_inv, 0) + COALESCE(j.total_jrn, 0) - COALESCE(p.total_pay, 0)  AS net_outstanding,
        COALESCE(pt.busy_closing_balance, 0)                                        AS busy_bal
    FROM parties pt
    LEFT JOIN bills b ON b.party_id = pt.id
    LEFT JOIN inv_sum i ON i.party_id = pt.id
    LEFT JOIN jrn_sum j ON j.party_id = pt.id
    LEFT JOIN pay_sum p ON p.party_id = pt.id
    WHERE pt.is_active = true
      AND ABS(COALESCE(b.bills_out, 0) - (COALESCE(i.total_inv, 0) + COALESCE(j.total_jrn, 0) - COALESCE(p.total_pay, 0))) > 1000
    ORDER BY ABS(COALESCE(b.bills_out, 0) - (COALESCE(i.total_inv, 0) + COALESCE(j.total_jrn, 0) - COALESCE(p.total_pay, 0))) DESC
    LIMIT 30
""")).fetchall()

print(f"{'Party':<42} {'Bills Out':>15} {'Net Outstanding':>16} {'BUSY Bal':>15} {'Gap (Bills-Net)':>16}")
print("-" * 108)
for r in result:
    diff = float(r.bills_outstanding) - float(r.net_outstanding)
    print(f"{r.name[:42]:<42} {float(r.bills_outstanding):>15,.2f} {float(r.net_outstanding):>16,.2f} {float(r.busy_bal):>15,.2f} {diff:>16,.2f}")

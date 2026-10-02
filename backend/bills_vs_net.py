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
    , pay_unallocated AS (
        SELECT party_id, SUM(unallocated) AS on_account
        FROM payments WHERE is_deleted = false GROUP BY party_id
    ),
    pay_settled AS (
        SELECT party_id, SUM(settled_amount) AS matched_settlements
        FROM payments WHERE is_deleted = false GROUP BY party_id
    )
    SELECT
        pt.name,
        COALESCE(b.bills_out, 0) AS bill_based_receivable,
        COALESCE(i.total_inv, 0) + COALESCE(j.total_jrn, 0) - COALESCE(p.total_pay, 0) AS party_receivable,
        COALESCE(u.on_account, 0) AS on_account,
        COALESCE(s.matched_settlements, 0) AS matched_settlements,
        COALESCE(b.bills_out, 0) - (
            COALESCE(i.total_inv, 0) + COALESCE(j.total_jrn, 0) - COALESCE(p.total_pay, 0)
        ) AS bill_vs_party_difference,
        COALESCE(pt.busy_closing_balance, 0) AS busy_bal
    FROM parties pt
    LEFT JOIN bills b ON b.party_id = pt.id
    LEFT JOIN inv_sum i ON i.party_id = pt.id
    LEFT JOIN jrn_sum j ON j.party_id = pt.id
    LEFT JOIN pay_sum p ON p.party_id = pt.id
    LEFT JOIN pay_unallocated u ON u.party_id = pt.id
    LEFT JOIN pay_settled s ON s.party_id = pt.id
    WHERE pt.is_active = true
            AND ABS(COALESCE(b.bills_out, 0) - (COALESCE(i.total_inv, 0) + COALESCE(j.total_jrn, 0) - COALESCE(p.total_pay, 0))) > 1000
        ORDER BY ABS(COALESCE(b.bills_out, 0) - (COALESCE(i.total_inv, 0) + COALESCE(j.total_jrn, 0) - COALESCE(p.total_pay, 0))) DESC
    LIMIT 30
""")).fetchall()

print(f"{'Party':<38} {'Bill-based':>15} {'Party recv.':>15} {'On-account':>15} {'Matched':>15} {'Difference':>15}")
print("-" * 118)
for r in result:
    print(
        f"{r.name[:38]:<38} "
        f"{float(r.bill_based_receivable):>15,.2f} "
        f"{float(r.party_receivable):>15,.2f} "
        f"{float(r.on_account):>15,.2f} "
        f"{float(r.matched_settlements):>15,.2f} "
        f"{float(r.bill_vs_party_difference):>15,.2f}"
    )

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

session = SessionLocal()

# Simpler query - avoid self-join cartesian product
result = session.execute(text("""
    WITH bills AS (
        SELECT
            party_id,
            SUM(balance_due) AS bills_out,
            SUM(amount - balance_due) AS bill_paid,
            COUNT(*) FILTER (WHERE balance_due > 0 AND balance_due < amount) AS partial_bills,
            SUM(amount - balance_due) FILTER (WHERE balance_due > 0 AND balance_due < amount) AS partial_paid
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
        COALESCE(b.bill_paid, 0) AS bill_paid_or_allocated,
        COALESCE(b.partial_bills, 0) AS partial_bills,
        COALESCE(b.partial_paid, 0) AS partial_paid,
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

print(f"{'Party':<30} {'Bill open':>12} {'Bill paid':>12} {'Partial#':>9} {'Partial paid':>13} {'Party recv.':>12} {'On-account':>12} {'Diff':>12}")
print("-" * 122)
for r in result:
    print(
        f"{r.name[:30]:<30} "
        f"{float(r.bill_based_receivable):>12,.2f} "
        f"{float(r.bill_paid_or_allocated):>12,.2f} "
        f"{r.partial_bills:>9} "
        f"{float(r.partial_paid):>13,.2f} "
        f"{float(r.party_receivable):>12,.2f} "
        f"{float(r.on_account):>12,.2f} "
        f"{float(r.bill_vs_party_difference):>12,.2f}"
    )

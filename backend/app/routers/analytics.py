from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional

import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..paging import clamp_page, ilike_pattern

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=schemas.DashboardSummary)
def dashboard_summary(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    # Single query for all 6 aggregates — eliminates 5 sequential full-table scans
    row = db.execute(text("""
        SELECT
            (SELECT COUNT(*)
             FROM parties
             WHERE is_active = true)                                         AS total_parties,

            (SELECT COUNT(*)
             FROM invoices
             WHERE is_deleted = false)                                       AS invoices_count,

            COALESCE(
              (SELECT SUM(amount) FROM invoices WHERE is_deleted = false),
            0)                                                               AS total_invoiced,

            COALESCE(
              (SELECT SUM(amount) FROM payments WHERE is_deleted = false),
            0)                                                               AS total_collected,

            COALESCE(
              (SELECT SUM(amount) FROM journal_entries WHERE is_deleted = false),
            0)                                                               AS total_journal,

            COALESCE(
              (SELECT SUM(balance_due) FROM invoices WHERE is_deleted = false),
            0)                                                               AS total_bills_outstanding,

            COALESCE(
              (SELECT SUM(unallocated) FROM payments WHERE is_deleted = false),
            0) +
            COALESCE(
              (SELECT SUM(ABS(amount) - COALESCE((SELECT SUM(allocated_amount) FROM payment_allocations WHERE journal_id = j.id), 0)) FROM journal_entries j WHERE amount < 0 AND is_deleted = false),
            0)                                                               AS total_unallocated_payments,

                        COALESCE(
                            (SELECT SUM(settled_amount) FROM payments WHERE is_deleted = false),
                        0)                                                               AS total_matched_settlements,

                        (SELECT COUNT(*) FROM invoices
                         WHERE is_deleted = false AND balance_due > 0 AND balance_due < amount) AS partially_paid_bills_count,

                        COALESCE(
                            (SELECT SUM(amount - balance_due) FROM invoices
                             WHERE is_deleted = false AND balance_due > 0 AND balance_due < amount),
                        0)                                                               AS partially_paid_amount,

            (SELECT COUNT(*)
             FROM invoices
             WHERE is_deleted = false
               AND is_paid = false
               AND due_date < :now)                                          AS overdue_count,

            COALESCE(
              (SELECT SUM(amount) FROM payments WHERE is_deleted = false AND DATE(payment_date) = CURRENT_DATE),
            0)                                                               AS today_receipts
    """), {"now": now}).fetchone()

    total_outstanding = row.total_invoiced + row.total_journal - row.total_collected

    # Recent payments
    payments = (
        db.query(models.Payment)
        .filter(models.Payment.is_deleted == False)
        .order_by(models.Payment.payment_date.desc(), models.Payment.id.desc())
        .all()
    )

    # Top overdue parties
    overdue_rows = db.execute(text("""
        WITH p_agg AS (
            SELECT party_id, COUNT(id) AS bills_count, SUM(balance_due) AS outstanding, MIN(due_date) AS oldest_due
            FROM invoices WHERE is_deleted = false AND is_paid = false AND due_date < :now
            GROUP BY party_id
        )
        SELECT p.id, p.name, p_agg.outstanding, p_agg.bills_count,
               EXTRACT(DAY FROM (:now - p_agg.oldest_due)) AS overdue_days
        FROM p_agg
        JOIN parties p ON p.id = p_agg.party_id
        ORDER BY p_agg.outstanding DESC
        LIMIT 5
    """), {"now": now}).fetchall()

    top_overdue_parties = [
        schemas.OverduePartyOut(
            id=r.id, name=r.name, outstanding=r.outstanding,
            bills_count=r.bills_count, overdue_days=int(r.overdue_days)
        ) for r in overdue_rows
    ]

    # Monthly trend
    trend_rows = db.execute(text("""
        WITH months AS (
            SELECT date_trunc('month', d)::date AS month_date
            FROM generate_series(
                date_trunc('month', CURRENT_DATE - INTERVAL '5 months'),
                date_trunc('month', CURRENT_DATE),
                '1 month'::interval
            ) d
        ),
        inv_agg AS (
            SELECT date_trunc('month', invoice_date)::date AS month_date, SUM(amount) AS total_invoiced
            FROM invoices WHERE is_deleted = false GROUP BY 1
        ),
        pay_agg AS (
            SELECT date_trunc('month', payment_date)::date AS month_date, SUM(amount) AS total_collected
            FROM payments WHERE is_deleted = false GROUP BY 1
        )
        SELECT 
            TO_CHAR(m.month_date, 'Mon') AS month_name,
            COALESCE(i.total_invoiced, 0) AS invoiced,
            COALESCE(p.total_collected, 0) AS collected
        FROM months m
        LEFT JOIN inv_agg i ON m.month_date = i.month_date
        LEFT JOIN pay_agg p ON m.month_date = p.month_date
        ORDER BY m.month_date ASC
    """)).fetchall()

    monthly_trend = [
        schemas.CashFlowMonth(month=r.month_name, invoiced=r.invoiced, collected=r.collected)
        for r in trend_rows
    ]

    return schemas.DashboardSummary(
        total_parties=row.total_parties,
        total_invoiced=row.total_invoiced,
        total_collected=row.total_collected,
        total_journal=row.total_journal,
        total_outstanding=total_outstanding,
        total_bills_outstanding=row.total_bills_outstanding,
        total_unallocated_payments=row.total_unallocated_payments,
        total_bill_party_difference=row.total_bills_outstanding - total_outstanding,
        total_matched_settlements=row.total_matched_settlements,
        partially_paid_bills_count=row.partially_paid_bills_count,
        partially_paid_amount=row.partially_paid_amount,
        invoices_count=row.invoices_count,
        overdue_count=row.overdue_count,
        today_receipts=row.today_receipts,
        top_overdue_parties=top_overdue_parties,
        monthly_trend=monthly_trend,
        recent_payments=payments,
    )


@router.get("/parties", response_model=schemas.PaginatedResponse[schemas.PartySummary])
def party_summaries(
    skip: int = 0,
    limit: int = 1000000,
    search: str = "",
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Single JOIN + GROUP BY replaces O(N×5) correlated subqueries.
    # PostgreSQL FILTER clause aggregates multiple sums in one pass over joined rows.
    search_filter = f"%{search}%" if search else None

    result = db.execute(text("""
        WITH i_agg AS (
            SELECT party_id, 
                   SUM(amount) AS total_invoiced, 
                   COUNT(id) AS invoice_count
            FROM invoices WHERE is_deleted = false GROUP BY party_id
        ),
        p_agg AS (
            SELECT party_id, 
                   SUM(amount) AS total_paid, 
                   COUNT(id) AS payment_count
            FROM payments WHERE is_deleted = false GROUP BY party_id
        ),
        j_agg AS (
            SELECT party_id, 
                   SUM(amount) AS total_journal
            FROM journal_entries WHERE is_deleted = false GROUP BY party_id
        ),
        agg AS (
            SELECT
                p.id                                                                AS party_id,
                p.name                                                              AS party_name,
                COALESCE(i_agg.total_invoiced, 0)                                   AS total_invoiced,
                COALESCE(p_agg.total_paid, 0)                                       AS total_paid,
                COALESCE(j_agg.total_journal, 0)                                    AS total_journal,
                COALESCE(i_agg.invoice_count, 0)                                    AS invoice_count,
                COALESCE(p_agg.payment_count, 0)                                    AS payment_count
            FROM parties p
            LEFT JOIN i_agg ON i_agg.party_id = p.id
            LEFT JOIN p_agg ON p_agg.party_id = p.id
            LEFT JOIN j_agg ON j_agg.party_id = p.id
            WHERE p.is_active = true
              AND (:search IS NULL OR p.name LIKE :search)
        ),
        counted AS (
            SELECT *, COUNT(*) OVER() AS total_count,
                   (total_invoiced + total_journal - total_paid) AS outstanding
            FROM agg
        )
        SELECT *
        FROM counted
        ORDER BY party_name ASC
        LIMIT :limit OFFSET :skip
    """), {"search": search_filter, "skip": skip, "limit": limit}).fetchall()

    total = result[0].total_count if result else 0

    items = [
        schemas.PartySummary(
            party_id=row.party_id,
            party_name=row.party_name,
            total_invoiced=row.total_invoiced,
            total_paid=row.total_paid,
            total_journal=row.total_journal,
            outstanding=row.outstanding,
            invoice_count=row.invoice_count,
            payment_count=row.payment_count,
        )
        for row in result
    ]

    return schemas.PaginatedResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/ar-report/csv")
def download_ar_csv(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Fetch all parties with their balances
    result = db.execute(text("""
        WITH i_agg AS (
            SELECT party_id, SUM(amount) AS total_invoiced, COUNT(id) AS invoice_count
            FROM invoices WHERE is_deleted = false GROUP BY party_id
        ),
        p_agg AS (
            SELECT party_id, SUM(amount) AS total_paid, COUNT(id) AS payment_count
            FROM payments WHERE is_deleted = false GROUP BY party_id
        ),
        j_agg AS (
            SELECT party_id, SUM(amount) AS total_journal
            FROM journal_entries WHERE is_deleted = false GROUP BY party_id
        ),
        agg AS (
            SELECT
                p.name AS party_name,
                COALESCE(i_agg.total_invoiced, 0) AS total_invoiced,
                COALESCE(p_agg.total_paid, 0) AS total_paid,
                COALESCE(j_agg.total_journal, 0) AS total_journal,
                (COALESCE(i_agg.total_invoiced, 0) + COALESCE(j_agg.total_journal, 0) - COALESCE(p_agg.total_paid, 0)) AS outstanding
            FROM parties p
            LEFT JOIN i_agg ON i_agg.party_id = p.id
            LEFT JOIN p_agg ON p_agg.party_id = p.id
            LEFT JOIN j_agg ON j_agg.party_id = p.id
            WHERE p.is_active = true
        )
        SELECT * FROM agg
        WHERE outstanding > 0
        ORDER BY party_name ASC
    """)).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Party Name", "Total Invoiced", "Total Paid", "Total Journal", "Net Pending (Outstanding)"])

    for row in result:
        writer.writerow([
            row.party_name,
            f"{row.total_invoiced:.2f}",
            f"{row.total_paid:.2f}",
            f"{row.total_journal:.2f}",
            f"{row.outstanding:.2f}"
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=ar_report_{datetime.now().strftime('%Y%m%d')}.csv"}
    )


def _csv_response(output: io.StringIO, filename: str) -> StreamingResponse:
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/party-balances/csv")
def download_party_balances_csv(
    party_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rows = db.execute(text("""
        WITH inv AS (
            SELECT party_id, SUM(amount) invoiced, SUM(balance_due) bill_receivable
            FROM invoices WHERE is_deleted = false GROUP BY party_id
        ), pay AS (
            SELECT party_id, SUM(amount) paid, SUM(unallocated) on_account,
                   SUM(settled_amount) settled
            FROM payments WHERE is_deleted = false GROUP BY party_id
        ), jrn AS (
            SELECT party_id, SUM(amount) journal FROM journal_entries
            WHERE is_deleted = false GROUP BY party_id
        )
        SELECT p.id, p.name, COALESCE(inv.invoiced,0) invoiced,
               COALESCE(inv.bill_receivable,0) bill_receivable,
               COALESCE(pay.paid,0) paid, COALESCE(pay.on_account,0) on_account,
               COALESCE(pay.settled,0) settled, COALESCE(jrn.journal,0) journal,
               COALESCE(inv.invoiced,0)+COALESCE(jrn.journal,0)-COALESCE(pay.paid,0) party_receivable
        FROM parties p LEFT JOIN inv ON inv.party_id=p.id
        LEFT JOIN pay ON pay.party_id=p.id LEFT JOIN jrn ON jrn.party_id=p.id
        WHERE p.is_active = true AND (:party_id IS NULL OR p.id=:party_id)
        ORDER BY p.name
    """), {"party_id": party_id}).fetchall()
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["Party", "Invoiced", "Bill Receivable", "Paid", "Journal", "On Account", "Matched Settlement", "Party Receivable"])
    for row in rows:
        writer.writerow([row.name, row.invoiced, row.bill_receivable, row.paid, row.journal, row.on_account, row.settled, row.party_receivable])
    return _csv_response(output, f"party_balances_{datetime.now().strftime('%Y%m%d')}.csv")


@router.get("/bill-balances/csv")
def download_bill_balances_csv(
    party_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rows = db.execute(text("""
        SELECT i.invoice_number, i.invoice_date, p.name party, i.amount,
               i.amount-i.balance_due bill_paid, i.balance_due,
               CASE WHEN i.balance_due <= 0 THEN 'PAID'
                    WHEN i.balance_due < i.amount THEN 'PARTIAL' ELSE 'UNPAID' END status
        FROM invoices i JOIN parties p ON p.id=i.party_id
        WHERE i.is_deleted = false AND (:party_id IS NULL OR i.party_id=:party_id)
        ORDER BY p.name, i.invoice_date, i.invoice_number
    """), {"party_id": party_id}).fetchall()
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["Invoice", "Date", "Party", "Amount", "Bill Paid/Allocated", "Bill Receivable", "Status"])
    for row in rows:
        writer.writerow([row.invoice_number, row.invoice_date, row.party, row.amount, row.bill_paid, row.balance_due, row.status])
    return _csv_response(output, f"bill_balances_{datetime.now().strftime('%Y%m%d')}.csv")


@router.get("/payment-ledger/csv")
def download_payment_ledger_csv(
    party_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rows = db.execute(text("""
        SELECT pay.id, pay.payment_date, p.name party, pay.amount,
               COALESCE(a.bill_allocated,0) bill_allocated,
               COALESCE(pay.settled_amount,0) matched_settlement,
               COALESCE(pay.unallocated,0) on_account,
               pay.mode, pay.note
        FROM payments pay JOIN parties p ON p.id=pay.party_id
        LEFT JOIN (SELECT payment_id, SUM(allocated_amount) bill_allocated
                   FROM payment_allocations WHERE payment_id IS NOT NULL GROUP BY payment_id) a
          ON a.payment_id=pay.id
        WHERE pay.is_deleted = false AND (:party_id IS NULL OR pay.party_id=:party_id)
        ORDER BY pay.payment_date, pay.id
    """), {"party_id": party_id}).fetchall()
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["Payment ID", "Date", "Party", "Amount", "Bill Allocated", "Matched Settlement", "On Account", "Mode", "Note"])
    for row in rows:
        writer.writerow([row.id, row.payment_date, row.party, row.amount, row.bill_allocated, row.matched_settlement, row.on_account, row.mode, row.note])
    return _csv_response(output, f"payment_ledger_{datetime.now().strftime('%Y%m%d')}.csv")


@router.get("/party/{party_id}", response_model=schemas.PartySummary)
def party_analytics(
    party_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.execute(text("""
        WITH i_agg AS (
            SELECT party_id, SUM(amount) AS total_invoiced, COUNT(id) AS invoice_count
            FROM invoices WHERE is_deleted = false AND party_id = :party_id GROUP BY party_id
        ),
        p_agg AS (
            SELECT party_id, SUM(amount) AS total_paid, COUNT(id) AS payment_count
            FROM payments WHERE is_deleted = false AND party_id = :party_id GROUP BY party_id
        ),
        j_agg AS (
            SELECT party_id, SUM(amount) AS total_journal
            FROM journal_entries WHERE is_deleted = false AND party_id = :party_id GROUP BY party_id
        )
        SELECT
            p.id                                                                AS party_id,
            p.name                                                              AS party_name,
            COALESCE(i_agg.total_invoiced, 0)                                   AS total_invoiced,
            COALESCE(p_agg.total_paid, 0)                                       AS total_paid,
            COALESCE(j_agg.total_journal, 0)                                    AS total_journal,
            COALESCE(i_agg.invoice_count, 0)                                    AS invoice_count,
            COALESCE(p_agg.payment_count, 0)                                    AS payment_count
        FROM parties p
        LEFT JOIN i_agg ON i_agg.party_id = p.id
        LEFT JOIN p_agg ON p_agg.party_id = p.id
        LEFT JOIN j_agg ON j_agg.party_id = p.id
        WHERE p.id = :party_id
    """), {"party_id": party_id}).fetchone()

    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Party not found")

    outstanding = row.total_invoiced + row.total_journal - row.total_paid
    return schemas.PartySummary(
        party_id=row.party_id,
        party_name=row.party_name,
        total_invoiced=row.total_invoiced,
        total_paid=row.total_paid,
        total_journal=row.total_journal,
        outstanding=outstanding,
        invoice_count=row.invoice_count,
        payment_count=row.payment_count,
    )


@router.get("/cashflow", response_model=List[schemas.CashFlowMonth])
def cashflow_report(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Get last 6 months of cashflow
    result = db.execute(text("""
        WITH months AS (
            SELECT date_trunc('month', d)::date AS month_date
            FROM generate_series(
                date_trunc('month', CURRENT_DATE - INTERVAL '5 months'),
                date_trunc('month', CURRENT_DATE),
                '1 month'::interval
            ) d
        ),
        inv_agg AS (
            SELECT date_trunc('month', invoice_date)::date AS month_date, SUM(amount) AS total_invoiced
            FROM invoices WHERE is_deleted = false GROUP BY 1
        ),
        pay_agg AS (
            SELECT date_trunc('month', payment_date)::date AS month_date, SUM(amount) AS total_collected
            FROM payments WHERE is_deleted = false GROUP BY 1
        )
        SELECT 
            TO_CHAR(m.month_date, 'Mon YYYY') AS month_name,
            COALESCE(i.total_invoiced, 0) AS invoiced,
            COALESCE(p.total_collected, 0) AS collected
        FROM months m
        LEFT JOIN inv_agg i ON m.month_date = i.month_date
        LEFT JOIN pay_agg p ON m.month_date = p.month_date
        ORDER BY m.month_date ASC
    """)).fetchall()
    
    return [
        schemas.CashFlowMonth(
            month=row.month_name,
            invoiced=row.invoiced,
            collected=row.collected
        ) for row in result
    ]


@router.get("/aging", response_model=schemas.PaginatedResponse[schemas.AgingBucket])
def aging_report(
    skip: int = 0,
    limit: int = 1000000,
    search: str = "",
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    date_30 = now - timedelta(days=30)
    date_60 = now - timedelta(days=60)
    date_90 = now - timedelta(days=90)
    search_filter = f"%{search}%" if search else None

    # Single CTE: compute aging buckets, get total count via window function,
    # and paginate — all in one round trip to the database.
    result = db.execute(text("""
        WITH aging_raw AS (
            SELECT
                p.id                                                                AS party_id,
                p.name                                                              AS party_name,
                COALESCE(SUM(i.balance_due) FILTER (
                    WHERE COALESCE(i.due_date, i.invoice_date) >= :date_30
                ), 0)                                                               AS current_bucket,
                COALESCE(SUM(i.balance_due) FILTER (
                    WHERE COALESCE(i.due_date, i.invoice_date) < :date_30
                      AND COALESCE(i.due_date, i.invoice_date) >= :date_60
                ), 0)                                                               AS days_31_60,
                COALESCE(SUM(i.balance_due) FILTER (
                    WHERE COALESCE(i.due_date, i.invoice_date) < :date_60
                      AND COALESCE(i.due_date, i.invoice_date) >= :date_90
                ), 0)                                                               AS days_61_90,
                COALESCE(SUM(i.balance_due) FILTER (
                    WHERE COALESCE(i.due_date, i.invoice_date) < :date_90
                ), 0)                                                               AS over_90
            FROM parties p
            JOIN invoices i ON i.party_id = p.id
            WHERE p.is_active = true
              AND i.is_deleted = false
              AND i.is_paid = false
              AND i.balance_due > 0
              AND (:search IS NULL OR p.name LIKE :search)
            GROUP BY p.id, p.name
        ),
        final AS (
            SELECT *,
                   (current_bucket + days_31_60 + days_61_90 + over_90) AS total_amount,
                   COUNT(*) OVER()                                        AS total_count
            FROM aging_raw
        )
        SELECT * FROM final
        ORDER BY total_amount DESC
        LIMIT :limit OFFSET :skip
    """), {
        "now": now, "date_30": date_30, "date_60": date_60, "date_90": date_90,
        "search": search_filter, "skip": skip, "limit": limit,
    }).fetchall()

    total = result[0].total_count if result else 0

    items = [
        schemas.AgingBucket(
            party_id=row.party_id,
            party_name=row.party_name,
            current=row.current_bucket,
            days_31_60=row.days_31_60,
            days_61_90=row.days_61_90,
            over_90=row.over_90,
            total=row.total_amount,
        )
        for row in result
    ]

    return schemas.PaginatedResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


# F12 — Collections breakdown by payment mode
@router.get("/collections-by-mode", response_model=List[schemas.ModeBreakdown])
def collections_by_mode(
    from_date: str | None = None,
    to_date: str | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from sqlalchemy import case
    query = db.execute(text("""
        SELECT
            COALESCE(mode, 'cash') AS mode,
            COUNT(*)               AS count,
            COALESCE(SUM(amount), 0) AS total
        FROM payments
        WHERE is_deleted = false
          AND (:from_date IS NULL OR payment_date >= :from_date)
          AND (:to_date IS NULL OR payment_date <= :to_date)
        GROUP BY COALESCE(mode, 'cash')
        ORDER BY total DESC
    """), {
        "from_date": from_date,
        "to_date": to_date,
    }).fetchall()

    return [
        schemas.ModeBreakdown(mode=row.mode, total=row.total, count=row.count)
        for row in query
    ]


@router.get("/by-agent", response_model=List[schemas.GroupedAnalytics])
def agent_analytics(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.execute(text("""
        WITH i_agg AS (
            SELECT party_id, SUM(amount) AS total_invoiced
            FROM invoices WHERE is_deleted = false GROUP BY party_id
        ),
        p_agg AS (
            SELECT party_id, SUM(amount) AS total_paid
            FROM payments WHERE is_deleted = false GROUP BY party_id
        ),
        j_agg AS (
            SELECT party_id, SUM(amount) AS total_journal
            FROM journal_entries WHERE is_deleted = false GROUP BY party_id
        ),
        agg AS (
            SELECT
                COALESCE(p.agent_name, 'Unassigned') AS group_name,
                COUNT(p.id) AS party_count,
                SUM(COALESCE(i_agg.total_invoiced, 0)) AS total_invoiced,
                SUM(COALESCE(p_agg.total_paid, 0)) AS total_paid,
                SUM(COALESCE(j_agg.total_journal, 0)) AS total_journal
            FROM parties p
            LEFT JOIN i_agg ON i_agg.party_id = p.id
            LEFT JOIN p_agg ON p_agg.party_id = p.id
            LEFT JOIN j_agg ON j_agg.party_id = p.id
            WHERE p.is_active = true
            GROUP BY COALESCE(p.agent_name, 'Unassigned')
        )
        SELECT *, (total_invoiced + total_journal - total_paid) AS outstanding
        FROM agg
        ORDER BY outstanding DESC
    """)).fetchall()

    return [
        schemas.GroupedAnalytics(
            group_name=row.group_name,
            total_invoiced=row.total_invoiced,
            total_paid=row.total_paid,
            total_journal=row.total_journal,
            outstanding=row.outstanding,
            party_count=row.party_count,
        ) for row in query
    ]


@router.get("/by-area", response_model=List[schemas.GroupedAnalytics])
def area_analytics(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.execute(text("""
        WITH i_agg AS (
            SELECT party_id, SUM(amount) AS total_invoiced
            FROM invoices WHERE is_deleted = false GROUP BY party_id
        ),
        p_agg AS (
            SELECT party_id, SUM(amount) AS total_paid
            FROM payments WHERE is_deleted = false GROUP BY party_id
        ),
        j_agg AS (
            SELECT party_id, SUM(amount) AS total_journal
            FROM journal_entries WHERE is_deleted = false GROUP BY party_id
        ),
        agg AS (
            SELECT
                COALESCE(p.area, 'Unassigned') AS group_name,
                COUNT(p.id) AS party_count,
                SUM(COALESCE(i_agg.total_invoiced, 0)) AS total_invoiced,
                SUM(COALESCE(p_agg.total_paid, 0)) AS total_paid,
                SUM(COALESCE(j_agg.total_journal, 0)) AS total_journal
            FROM parties p
            LEFT JOIN i_agg ON i_agg.party_id = p.id
            LEFT JOIN p_agg ON p_agg.party_id = p.id
            LEFT JOIN j_agg ON j_agg.party_id = p.id
            WHERE p.is_active = true
            GROUP BY COALESCE(p.area, 'Unassigned')
        )
        SELECT *, (total_invoiced + total_journal - total_paid) AS outstanding
        FROM agg
        ORDER BY outstanding DESC
    """)).fetchall()

    return [
        schemas.GroupedAnalytics(
            group_name=row.group_name,
            total_invoiced=row.total_invoiced,
            total_paid=row.total_paid,
            total_journal=row.total_journal,
            outstanding=row.outstanding,
            party_count=row.party_count,
        ) for row in query
    ]


@router.get("/executive-summary", response_model=schemas.ExecutiveSummary)
def executive_summary(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    date_60 = now - timedelta(days=60)
    
    # We do a massive aggregation here
    res = db.execute(text("""
        WITH agg AS (
            SELECT 
                (SELECT COALESCE(SUM(amount), 0) FROM invoices WHERE is_deleted=false) AS total_invoiced,
                (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE is_deleted=false) AS total_paid,
                (SELECT COALESCE(SUM(amount), 0) FROM journal_entries WHERE is_deleted=false) AS total_journal,
                (SELECT COALESCE(SUM(unallocated), 0) FROM payments WHERE is_deleted=false) AS unallocated_advance,
                (SELECT COALESCE(SUM(balance_due), 0) FROM invoices WHERE is_deleted=false AND is_paid=false AND COALESCE(due_date, invoice_date) < :date_60) AS at_risk
        ),
        party_bals AS (
            SELECT p.id,
                   (SELECT COALESCE(SUM(amount), 0) FROM invoices WHERE party_id = p.id AND is_deleted=false) +
                   (SELECT COALESCE(SUM(amount), 0) FROM journal_entries WHERE party_id = p.id AND is_deleted=false) -
                   (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE party_id = p.id AND is_deleted=false) AS outstanding
            FROM parties p
            WHERE p.is_active = true
        ),
        top_10 AS (
            SELECT COALESCE(SUM(outstanding), 0) AS sum_top_10 
            FROM (SELECT outstanding FROM party_bals ORDER BY outstanding DESC LIMIT 10) t
        )
        SELECT 
            agg.total_invoiced, 
            agg.total_paid, 
            agg.total_journal, 
            agg.unallocated_advance,
            agg.at_risk,
            (agg.total_invoiced + agg.total_journal - agg.total_paid) AS total_outstanding,
            top_10.sum_top_10
        FROM agg, top_10
    """), {"date_60": date_60}).fetchone()

    total_inv = res.total_invoiced or 1 # prevent div/0
    total_out = res.total_outstanding or 1 # prevent div/0

    dso = (res.total_outstanding / total_inv) * 365 if total_inv > 0 else 0
    at_risk_ratio = (res.at_risk / total_out) * 100 if total_out > 0 else 0
    journal_adj_ratio = (res.total_journal / total_inv) * 100 if total_inv > 0 else 0
    top_10_conc = (res.sum_top_10 / total_out) * 100 if total_out > 0 else 0

    return schemas.ExecutiveSummary(
        dso_days=dso,
        unallocated_advance_pool=res.unallocated_advance,
        at_risk_ratio=at_risk_ratio,
        journal_adjustment_ratio=journal_adj_ratio,
        top_10_concentration=top_10_conc
    )


@router.get("/fabric-metrics", response_model=List[schemas.FabricItemMetrics])
def fabric_metrics(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Fabric / Unit Economics
    res = db.execute(text("""
        SELECT 
            item_name,
            SUM(meter) AS total_meterage,
            SUM(total) AS sum_total,
            COUNT(DISTINCT invoice_id) as invoice_count
        FROM invoice_items
        GROUP BY item_name
        ORDER BY total_meterage DESC
    """)).fetchall()

    items = []
    for row in res:
        avg_realized = (row.sum_total / row.total_meterage) if row.total_meterage and row.total_meterage > 0 else 0
        avg_ticket = (row.sum_total / row.invoice_count) if row.invoice_count and row.invoice_count > 0 else 0
        items.append(schemas.FabricItemMetrics(
            item_name=row.item_name,
            total_meterage=row.total_meterage or 0,
            avg_realized_rate=avg_realized,
            avg_ticket_size=avg_ticket
        ))
    return items

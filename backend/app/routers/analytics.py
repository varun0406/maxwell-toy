from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

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

            (SELECT COUNT(*)
             FROM invoices
             WHERE is_deleted = false
               AND is_paid = false
               AND due_date < :now)                                          AS overdue_count
    """), {"now": now}).fetchone()

    total_outstanding = row.total_invoiced + row.total_journal - row.total_collected

    # Recent payments
    payments = (
        db.query(models.Payment)
        .filter(models.Payment.is_deleted == False)
        .order_by(models.Payment.payment_date.desc(), models.Payment.id.desc())
        .all()
    )

    return schemas.DashboardSummary(
        total_parties=row.total_parties,
        total_invoiced=row.total_invoiced,
        total_collected=row.total_collected,
        total_journal=row.total_journal,
        total_outstanding=total_outstanding,
        invoices_count=row.invoices_count,
        overdue_count=row.overdue_count,
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
        ORDER BY outstanding DESC
        OFFSET :skip LIMIT :limit
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
        OFFSET :skip LIMIT :limit
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

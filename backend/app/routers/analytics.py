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
        WITH agg AS (
            SELECT
                p.id                                                                AS party_id,
                p.name                                                              AS party_name,
                COALESCE(SUM(i.amount)   FILTER (WHERE i.is_deleted = false), 0)   AS total_invoiced,
                COALESCE(SUM(pay.amount) FILTER (WHERE pay.is_deleted = false), 0) AS total_paid,
                COALESCE(SUM(j.amount)   FILTER (WHERE j.is_deleted = false), 0)   AS total_journal,
                COUNT(i.id)              FILTER (WHERE i.is_deleted = false)        AS invoice_count,
                COUNT(pay.id)            FILTER (WHERE pay.is_deleted = false)      AS payment_count
            FROM parties p
            LEFT JOIN invoices       i   ON i.party_id   = p.id
            LEFT JOIN payments       pay ON pay.party_id = p.id
            LEFT JOIN journal_entries j  ON j.party_id   = p.id
            WHERE p.is_active = true
              AND (:search IS NULL OR p.name LIKE :search)
            GROUP BY p.id, p.name
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
        SELECT
            p.id                                                                AS party_id,
            p.name                                                              AS party_name,
            COALESCE(SUM(i.amount)   FILTER (WHERE i.is_deleted = false), 0)   AS total_invoiced,
            COALESCE(SUM(pay.amount) FILTER (WHERE pay.is_deleted = false), 0) AS total_paid,
            COALESCE(SUM(j.amount)   FILTER (WHERE j.is_deleted = false), 0)   AS total_journal,
            COUNT(i.id)              FILTER (WHERE i.is_deleted = false)        AS invoice_count,
            COUNT(pay.id)            FILTER (WHERE pay.is_deleted = false)      AS payment_count
        FROM parties p
        LEFT JOIN invoices        i   ON i.party_id   = p.id
        LEFT JOIN payments        pay ON pay.party_id = p.id
        LEFT JOIN journal_entries j   ON j.party_id   = p.id
        WHERE p.id = :party_id
        GROUP BY p.id, p.name
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

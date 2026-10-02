from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..paging import clamp_page, ilike_pattern

router = APIRouter(prefix="/parties", tags=["parties"])


def _get_party_or_404(party_id: int, db: Session) -> models.Party:
    party = (
        db.query(models.Party)
        .filter(models.Party.id == party_id)
        .first()
    )
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    return party


@router.get("/", response_model=schemas.PaginatedResponse[schemas.PartyWithBalance])
def list_parties(
    skip: int = 0,
    limit: int = 50,
    search: str = "",
    unpaid_only: bool = False,
    agent: Optional[str] = None,
    sort: str = Query("name", pattern="^(name|dues)$"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    skip, limit = clamp_page(skip, limit)
    search_filter = ilike_pattern(search)
    order_sql = (
        "CASE WHEN reminder_date IS NULL THEN 1 ELSE 0 END, reminder_date ASC NULLS LAST, outstanding DESC, name ASC"
        if (sort == "dues" or unpaid_only)
        else "name ASC"
    )

    rows = db.execute(text(f"""
        WITH i_agg AS (
            SELECT party_id, 
                   SUM(amount) AS total_invoiced,
                   SUM(balance_due) AS bills_outstanding,
                   MIN(COALESCE(due_date, invoice_date)) FILTER (WHERE is_paid = false AND balance_due > 0) AS oldest_due
            FROM invoices WHERE COALESCE(is_deleted, false) = false GROUP BY party_id
        ),
        p_agg AS (
            SELECT party_id, 
                   SUM(amount) AS total_paid,
                   SUM(unallocated) AS unallocated_payments
            FROM payments WHERE COALESCE(is_deleted, false) = false GROUP BY party_id
        ),
        j_agg AS (
            SELECT party_id, SUM(amount) AS total_journal
            FROM journal_entries WHERE COALESCE(is_deleted, false) = false GROUP BY party_id
        ),
        j_unalloc AS (
            SELECT party_id, 
                   SUM(ABS(amount) - COALESCE((SELECT SUM(allocated_amount) FROM payment_allocations WHERE journal_id = j.id), 0)) AS unallocated_journals
            FROM journal_entries j
            WHERE amount < 0 AND COALESCE(is_deleted, false) = false GROUP BY party_id
        ),
        filtered AS (
            SELECT
                p.id,
                p.name,
                p.phone,
                p.email,
                p.agent_name,
                p.billing_address_line1,
                p.billing_address_line2,
                p.billing_address_line3,
                p.billing_city,
                p.shipping_address_line1,
                p.shipping_address_line2,
                p.shipping_address_line3,
                p.shipping_city,
                p.area,
                p.gstin,
                p.notes,
                p.reminder_date,
                p.is_active,
                p.created_at,
                p.busy_closing_balance,
                COALESCE(i_agg.total_invoiced, 0) AS total_invoiced,
                COALESCE(p_agg.total_paid, 0) AS total_paid,
                COALESCE(j_agg.total_journal, 0) AS total_journal,
                (COALESCE(i_agg.total_invoiced, 0) + COALESCE(j_agg.total_journal, 0) - COALESCE(p_agg.total_paid, 0)) AS outstanding,
                COALESCE(i_agg.bills_outstanding, 0) AS bills_outstanding,
                COALESCE(p_agg.unallocated_payments, 0) + COALESCE(j_unalloc.unallocated_journals, 0) AS unallocated_payments,
                EXTRACT(DAY FROM (CURRENT_TIMESTAMP - i_agg.oldest_due)) AS overdue_days
            FROM parties p
            LEFT JOIN i_agg ON i_agg.party_id = p.id
            LEFT JOIN p_agg ON p_agg.party_id = p.id
            LEFT JOIN j_agg ON j_agg.party_id = p.id
            LEFT JOIN j_unalloc ON j_unalloc.party_id = p.id
                WHERE COALESCE(p.is_active, true) = true
              AND (
                    :search IS NULL
                      OR p.name ILIKE :search ESCAPE '\\'
                      OR COALESCE(p.phone, '') ILIKE :search ESCAPE '\\'
                      OR COALESCE(p.email, '') ILIKE :search ESCAPE '\\'
                      OR COALESCE(p.area, '') ILIKE :search ESCAPE '\\'
                      OR COALESCE(p.agent_name, '') ILIKE :search ESCAPE '\\'
                      OR COALESCE(p.billing_city, '') ILIKE :search ESCAPE '\\'
                      OR COALESCE(p.shipping_city, '') ILIKE :search ESCAPE '\\'
                      OR COALESCE(p.gstin, '') ILIKE :search ESCAPE '\\'
              )
              AND (:agent IS NULL OR p.agent_name = :agent)
              AND (
                    :unpaid_only = false
                      OR ABS(COALESCE(i_agg.total_invoiced, 0) + COALESCE(j_agg.total_journal, 0) - COALESCE(p_agg.total_paid, 0)) > 0.01
                      OR ABS(COALESCE(i_agg.bills_outstanding, 0)) > 0.01
                      OR ABS(COALESCE(p_agg.unallocated_payments, 0)) > 0.01
              )
        )
        SELECT *, COUNT(*) OVER() AS total_count
        FROM filtered
        ORDER BY {order_sql}
        LIMIT :limit OFFSET :skip
    """), {
        "search": search_filter,
        "unpaid_only": unpaid_only,
        "agent": agent,
        "skip": skip,
        "limit": limit,
    }).fetchall()

    total = rows[0].total_count if rows else 0

    result = [
        schemas.PartyWithBalance(
            id=row.id,
            name=row.name,
            phone=row.phone,
            email=row.email,
            agent_name=row.agent_name,
            billing_address_line1=row.billing_address_line1,
            billing_address_line2=row.billing_address_line2,
            billing_address_line3=row.billing_address_line3,
            billing_city=row.billing_city,
            shipping_address_line1=row.shipping_address_line1,
            shipping_address_line2=row.shipping_address_line2,
            shipping_address_line3=row.shipping_address_line3,
            shipping_city=row.shipping_city,
            area=row.area,
            gstin=row.gstin,
            notes=row.notes,
            reminder_date=row.reminder_date,
            is_active=row.is_active,
            created_at=row.created_at,
            total_invoiced=row.total_invoiced,
            total_paid=row.total_paid,
            total_journal=row.total_journal,
            outstanding=row.outstanding,
            bills_outstanding=row.bills_outstanding,
            unallocated_payments=row.unallocated_payments,
            overdue_days=int(row.overdue_days) if row.overdue_days is not None else 0,
        )
        for row in rows
    ]

    return schemas.PaginatedResponse(
        items=result,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("/", response_model=schemas.PartyOut, status_code=201)
def create_party(
    payload: schemas.PartyCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    party = models.Party(**payload.model_dump(), created_by=current_user.id)
    db.add(party)
    db.commit()
    db.refresh(party)
    return party


@router.get("/{party_id}", response_model=schemas.PartyWithBalance)
def get_party(
    party_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.execute(text("""
        SELECT
            p.id,
            p.name,
            p.phone,
            p.email,
            p.agent_name,
            p.billing_address_line1,
            p.billing_address_line2,
            p.billing_address_line3,
            p.billing_city,
            p.shipping_address_line1,
            p.shipping_address_line2,
            p.shipping_address_line3,
            p.shipping_city,
            p.area,
            p.gstin,
            p.notes,
            p.reminder_date,
            p.is_active,
            p.created_at,
            COALESCE((SELECT SUM(amount) FROM invoices WHERE party_id = p.id AND COALESCE(is_deleted, false) = false), 0) AS total_invoiced,
            COALESCE((SELECT SUM(amount) FROM payments WHERE party_id = p.id AND COALESCE(is_deleted, false) = false), 0) AS total_paid,
            COALESCE((SELECT SUM(amount) FROM journal_entries WHERE party_id = p.id AND COALESCE(is_deleted, false) = false), 0) AS total_journal,
            
            COALESCE((SELECT SUM(balance_due) FROM invoices WHERE party_id = p.id AND COALESCE(is_deleted, false) = false), 0) AS bills_outstanding,
            COALESCE((SELECT SUM(unallocated) FROM payments WHERE party_id = p.id AND COALESCE(is_deleted, false) = false), 0) +
            COALESCE((SELECT SUM(ABS(amount) - COALESCE((SELECT SUM(allocated_amount) FROM payment_allocations WHERE journal_id = j.id), 0)) FROM journal_entries j WHERE party_id = p.id AND amount < 0 AND COALESCE(is_deleted, false) = false), 0) AS unallocated_payments
        FROM parties p
        WHERE p.id = :party_id
    """), {"party_id": party_id}).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Party not found")

    outstanding = row.total_invoiced + row.total_journal - row.total_paid
    return schemas.PartyWithBalance(
        id=row.id,
        name=row.name,
        phone=row.phone,
        email=row.email,
        agent_name=row.agent_name,
        billing_address_line1=row.billing_address_line1,
        billing_address_line2=row.billing_address_line2,
        billing_address_line3=row.billing_address_line3,
        billing_city=row.billing_city,
        shipping_address_line1=row.shipping_address_line1,
        shipping_address_line2=row.shipping_address_line2,
        shipping_address_line3=row.shipping_address_line3,
        shipping_city=row.shipping_city,
        area=row.area,
        gstin=row.gstin,
        notes=row.notes,
        reminder_date=row.reminder_date,
        is_active=row.is_active,
        created_at=row.created_at,
        total_invoiced=row.total_invoiced,
        total_paid=row.total_paid,
        total_journal=row.total_journal,
        outstanding=outstanding,
        bills_outstanding=row.bills_outstanding,
        unallocated_payments=row.unallocated_payments,
    )


@router.put("/{party_id}", response_model=schemas.PartyOut)
def update_party(
    party_id: int,
    payload: schemas.PartyUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    party = _get_party_or_404(party_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(party, field, value)
    db.commit()
    db.refresh(party)
    return party


@router.delete("/{party_id}", status_code=204)
def delete_party(
    party_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    party = _get_party_or_404(party_id, db)
    party.is_active = False   # soft delete
    db.commit()


@router.get("/{party_id}/ledger", response_model=List[schemas.LedgerEntry])
def party_ledger(
    party_id: int,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify party exists
    _get_party_or_404(party_id, db)

    # SQL UNION ALL + window SUM() OVER() for running balance.
    # Replaces loading all ORM objects into Python, sorting in Python,
    # and computing running balance in Python — all done in a single DB query.
    rows = db.execute(text("""
        WITH ledger_raw AS (
            SELECT
                'invoice'           AS type,
                id                  AS record_id,
                invoice_date        AS date,
                invoice_number      AS reference,
                amount              AS amount,
                balance_due         AS balance_due,
                description         AS description
            FROM invoices
            WHERE party_id = :party_id AND is_deleted = false

            UNION ALL

            SELECT
                'payment'               AS type,
                id                      AS record_id,
                payment_date            AS date,
                'PMT-' || id::text      AS reference,
                -amount                 AS amount,
                NULL                    AS balance_due,
                NULL                    AS description
            FROM payments
            WHERE party_id = :party_id AND is_deleted = false

            UNION ALL

            SELECT
                'journal'               AS type,
                id                      AS record_id,
                entry_date              AS date,
                'JNL-' || id::text      AS reference,
                amount                  AS amount,
                NULL                    AS balance_due,
                description             AS description
            FROM journal_entries
            WHERE party_id = :party_id AND is_deleted = false
        ),
        with_balance AS (
            SELECT
                type,
                record_id,
                date,
                reference,
                amount,
                balance_due,
                description,
                SUM(amount) OVER (ORDER BY date, reference ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_balance
            FROM ledger_raw
        )
        SELECT *
        FROM with_balance
        WHERE (:from_date IS NULL OR date::date >= :from_date)
          AND (:to_date IS NULL OR date::date <= :to_date)
        ORDER BY date DESC, reference DESC
    """), {"party_id": party_id, "from_date": from_date, "to_date": to_date}).fetchall()

    return [
        schemas.LedgerEntry(
            type=row.type,
            record_id=row.record_id,
            date=row.date,
            reference=row.reference,
            amount=row.amount,
            balance_due=row.balance_due,
            running_balance=row.running_balance,
            description=row.description,
        )
        for row in rows
    ]


@router.post("/{party_id}/journal", response_model=schemas.JournalEntryOut, status_code=status.HTTP_201_CREATED)
def create_journal_entry(
    party_id: int,
    entry_in: schemas.JournalEntryCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    party = _get_party_or_404(party_id, db)

    db_entry = models.JournalEntry(
        party_id=party.id,
        created_by=current_user.id,
        amount=entry_in.amount,
        contra_amount=abs(entry_in.amount),
        account_id=entry_in.account_id,
        entry_date=entry_in.entry_date,
        description=entry_in.description,
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    
    result = schemas.JournalEntryOut.model_validate(db_entry)
    if db_entry.account_master:
        result.account_name = db_entry.account_master.name
    return result


@router.delete("/journal/{journal_id}", status_code=204)
def delete_journal(
    journal_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    jnl = (
        db.query(models.JournalEntry)
        .filter(
            models.JournalEntry.id == journal_id,
            models.JournalEntry.created_by == current_user.id,
            models.JournalEntry.is_deleted == False,
        )
        .first()
    )
    if not jnl:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    jnl.is_deleted = True
    db.commit()
    return None

from decimal import Decimal
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

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
    limit: int = 1000000,
    search: str = "",
    unpaid_only: bool = False,
    agent: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Single JOIN+GROUP BY query replaces correlated subqueries per party.
    # COUNT(*) OVER() window function gives total without a second query.
    # Also fixes the duplicate-query bug where .all() was called twice.
    search_filter = f"%{search}%" if search else None

    rows = db.execute(text("""
        WITH agg AS (
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
                (SELECT COALESCE(SUM(amount), 0) FROM invoices WHERE party_id = p.id AND is_deleted = false) AS total_invoiced,
                (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE party_id = p.id AND is_deleted = false) AS total_paid,
                (SELECT COALESCE(SUM(amount), 0) FROM journal_entries WHERE party_id = p.id AND is_deleted = false) AS total_journal
            FROM parties p
            WHERE p.is_active = true
              AND (:search IS NULL OR p.name LIKE :search)
              AND (:agent IS NULL OR p.agent_name = :agent)
        ),
        filtered AS (
            SELECT *,
                   (total_invoiced + total_journal - total_paid) AS outstanding
            FROM agg
            WHERE (:unpaid_only = false OR (total_invoiced + total_journal - total_paid) > 0)
        )
        SELECT *, COUNT(*) OVER() AS total_count
        FROM filtered
        ORDER BY name
        OFFSET :skip LIMIT :limit
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
            (SELECT COALESCE(SUM(amount), 0) FROM invoices WHERE party_id = p.id AND is_deleted = false) AS total_invoiced,
            (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE party_id = p.id AND is_deleted = false) AS total_paid,
            (SELECT COALESCE(SUM(amount), 0) FROM journal_entries WHERE party_id = p.id AND is_deleted = false) AS total_journal
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
                invoice_date        AS date,
                invoice_number      AS reference,
                amount              AS amount,
                balance_due         AS balance_due
            FROM invoices
            WHERE party_id = :party_id AND is_deleted = false

            UNION ALL

            SELECT
                'payment'               AS type,
                payment_date            AS date,
                'PMT-' || id::text      AS reference,
                -amount                 AS amount,
                NULL                    AS balance_due
            FROM payments
            WHERE party_id = :party_id AND is_deleted = false

            UNION ALL

            SELECT
                'journal'               AS type,
                entry_date              AS date,
                'JNL-' || id::text      AS reference,
                amount                  AS amount,
                NULL                    AS balance_due
            FROM journal_entries
            WHERE party_id = :party_id AND is_deleted = false
        )
        SELECT
            type,
            date,
            reference,
            amount,
            balance_due,
            SUM(amount) OVER (ORDER BY date, reference ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_balance
        FROM ledger_raw
        ORDER BY date, reference
    """), {"party_id": party_id}).fetchall()

    filtered_rows = []
    for row in rows:
        r_date = row.date.date() if hasattr(row.date, 'date') else row.date
        if from_date and r_date < from_date:
            continue
        if to_date and r_date > to_date:
            continue
        filtered_rows.append(row)

    return [
        schemas.LedgerEntry(
            type=row.type,
            date=row.date,
            reference=row.reference,
            amount=row.amount,
            balance_due=row.balance_due,
            running_balance=row.running_balance,
        )
        for row in filtered_rows
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
        entry_date=entry_in.entry_date,
        description=entry_in.description,
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry


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

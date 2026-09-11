from decimal import Decimal
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/parties", tags=["parties"])


def _get_party_or_404(party_id: int, user_id: int, db: Session) -> models.Party:
    party = (
        db.query(models.Party)
        .filter(models.Party.id == party_id, models.Party.created_by == user_id)
        .first()
    )
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    return party


def _compute_balance(party: models.Party) -> dict:
    total_invoiced = sum(i.amount for i in party.invoices) or Decimal("0")
    total_paid = sum(p.amount for p in party.payments) or Decimal("0")
    outstanding = total_invoiced - total_paid
    return {
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "outstanding": outstanding,
    }


@router.get("/", response_model=List[schemas.PartyWithBalance])
def list_parties(
    skip: int = 0,
    limit: int = 100,
    search: str = "",
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(models.Party).filter(
        models.Party.created_by == current_user.id,
        models.Party.is_active == True,
    )
    if search:
        query = query.filter(models.Party.name.ilike(f"%{search}%"))
    parties = query.order_by(models.Party.name).offset(skip).limit(limit).all()

    result = []
    for p in parties:
        bal = _compute_balance(p)
        result.append(schemas.PartyWithBalance(**schemas.PartyOut.model_validate(p).model_dump(), **bal))
    return result


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
    party = _get_party_or_404(party_id, current_user.id, db)
    bal = _compute_balance(party)
    return schemas.PartyWithBalance(**schemas.PartyOut.model_validate(party).model_dump(), **bal)


@router.put("/{party_id}", response_model=schemas.PartyOut)
def update_party(
    party_id: int,
    payload: schemas.PartyUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    party = _get_party_or_404(party_id, current_user.id, db)
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
    party = _get_party_or_404(party_id, current_user.id, db)
    party.is_active = False   # soft delete
    db.commit()


@router.get("/{party_id}/ledger", response_model=List[schemas.LedgerEntry])
def party_ledger(
    party_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    party = _get_party_or_404(party_id, current_user.id, db)

    entries = []
    for inv in party.invoices:
        if inv.is_deleted: continue
        entries.append({
            "type": "invoice",
            "date": inv.invoice_date,
            "reference": inv.invoice_number,
            "amount": inv.amount,
            "balance_due": inv.balance_due,
        })
    for pmt in party.payments:
        if pmt.is_deleted: continue
        entries.append({
            "type": "payment",
            "date": pmt.payment_date,
            "reference": f"PMT-{pmt.id}",
            "amount": -pmt.amount,
            "balance_due": None,
        })
    for jnl in party.journal_entries:
        if jnl.is_deleted: continue
        entries.append({
            "type": "journal",
            "date": jnl.entry_date,
            "reference": f"JNL-{jnl.id}",
            "amount": jnl.amount,
            "balance_due": None,
        })

    # Sort by date
    entries.sort(key=lambda e: e["date"])

    # Compute running balance
    running = Decimal("0")
    ledger = []
    for e in entries:
        running += e["amount"]
        ledger.append(
            schemas.LedgerEntry(
                type=e["type"],
                date=e["date"],
                reference=e["reference"],
                amount=e["amount"],
                balance_due=e.get("balance_due"),
                running_balance=running,
            )
        )
    return ledger


@router.post("/{party_id}/journal", response_model=schemas.JournalEntryOut, status_code=status.HTTP_201_CREATED)
def create_journal_entry(
    party_id: int,
    entry_in: schemas.JournalEntryCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    party = _get_party_or_404(party_id, current_user.id, db)

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
        .filter(models.JournalEntry.id == journal_id, models.JournalEntry.created_by == current_user.id, models.JournalEntry.is_deleted == False)
        .first()
    )
    if not jnl:
        raise HTTPException(status_code=404, detail="Journal entry not found")
        
    jnl.is_deleted = True
    db.commit()
    return None

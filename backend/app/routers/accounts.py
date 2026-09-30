from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import List, Optional
from ..database import get_db
from ..models import AccountMaster, JournalEntry
from ..schemas import AccountMasterCreate, AccountMasterOut

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/", response_model=List[AccountMasterOut])
def list_accounts(
    q: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all master accounts with their totals."""
    query = (
        db.query(
            AccountMaster,
            func.coalesce(func.sum(
                case(
                    (JournalEntry.is_deleted == False, JournalEntry.amount),
                    else_=0
                )
            ), 0).label("total_amount"),
            func.count(
                case(
                    (JournalEntry.is_deleted == False, JournalEntry.id),
                )
            ).label("entry_count"),
        )
        .outerjoin(JournalEntry, JournalEntry.account_id == AccountMaster.id)
        .group_by(AccountMaster.id)
    )

    if q:
        query = query.filter(AccountMaster.name.ilike(f"%{q}%"))

    query = query.order_by(AccountMaster.name)
    results = query.all()

    out = []
    for acct, total_amount, entry_count in results:
        out.append(AccountMasterOut(
            id=acct.id,
            name=acct.name,
            group_name=acct.group_name,
            is_active=acct.is_active,
            total_amount=total_amount,
            entry_count=entry_count,
            created_at=acct.created_at,
        ))
    return out


@router.get("/{account_id}", response_model=AccountMasterOut)
def get_account(account_id: int, db: Session = Depends(get_db)):
    acct = db.query(AccountMaster).filter(AccountMaster.id == account_id).first()
    if not acct:
        raise HTTPException(404, "Account not found")

    stats = (
        db.query(
            func.coalesce(func.sum(JournalEntry.amount), 0),
            func.count(JournalEntry.id),
        )
        .filter(JournalEntry.account_id == account_id, JournalEntry.is_deleted == False)
        .first()
    )

    return AccountMasterOut(
        id=acct.id,
        name=acct.name,
        group_name=acct.group_name,
        is_active=acct.is_active,
        total_amount=stats[0],
        entry_count=stats[1],
        created_at=acct.created_at,
    )


@router.get("/{account_id}/entries")
def get_account_entries(
    account_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Get all journal entries for a specific master account, with party details."""
    acct = db.query(AccountMaster).filter(AccountMaster.id == account_id).first()
    if not acct:
        raise HTTPException(404, "Account not found")

    entries = (
        db.query(JournalEntry)
        .filter(JournalEntry.account_id == account_id, JournalEntry.is_deleted == False)
        .order_by(JournalEntry.entry_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    total = (
        db.query(func.count(JournalEntry.id))
        .filter(JournalEntry.account_id == account_id, JournalEntry.is_deleted == False)
        .scalar()
    )

    return {
        "account": {
            "id": acct.id,
            "name": acct.name,
            "group_name": acct.group_name,
        },
        "total": total,
        "entries": [
            {
                "id": e.id,
                "party_id": e.party_id,
                "party_name": e.party.name if e.party else None,
                "amount": float(e.amount),
                "entry_date": e.entry_date.isoformat() if e.entry_date else None,
                "description": e.description,
            }
            for e in entries
        ],
    }


@router.post("/", response_model=AccountMasterOut)
def create_account(payload: AccountMasterCreate, db: Session = Depends(get_db)):
    existing = db.query(AccountMaster).filter(AccountMaster.name == payload.name).first()
    if existing:
        raise HTTPException(400, "Account with this name already exists")

    acct = AccountMaster(name=payload.name, group_name=payload.group_name)
    db.add(acct)
    db.commit()
    db.refresh(acct)

    return AccountMasterOut(
        id=acct.id,
        name=acct.name,
        group_name=acct.group_name,
        is_active=acct.is_active,
        total_amount=0,
        entry_count=0,
        created_at=acct.created_at,
    )

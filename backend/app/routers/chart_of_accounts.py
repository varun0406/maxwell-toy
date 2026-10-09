from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/chart-of-accounts", tags=["chart-of-accounts"])

@router.get("/", response_model=List[schemas.AccountOut])
def list_accounts(
    account_type: Optional[str] = None,
    q: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Account).filter(models.Account.active == True)
    if account_type:
        query = query.filter(models.Account.account_type == account_type)
    if q:
        query = query.filter(models.Account.name.ilike(f"%{q}%"))
    
    return query.order_by(models.Account.name).all()

@router.post("/", response_model=schemas.AccountOut)
def create_account(
    account: schemas.AccountCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # check for unique code if provided
    if account.code:
        exists = db.query(models.Account).filter(models.Account.code == account.code).first()
        if exists:
            raise HTTPException(status_code=400, detail="Account code already exists")
    
    db_acc = models.Account(**account.model_dump())
    db.add(db_acc)
    db.commit()
    db.refresh(db_acc)
    return db_acc

@router.get("/{account_id}/entries")
def get_account_ledger(
    account_id: int,
    skip: int = 0,
    limit: int = 50,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    lines = (
        db.query(models.VoucherLine)
        .join(models.Voucher)
        .filter(models.VoucherLine.account_id == account_id)
        .filter(models.Voucher.status == 'POSTED')
        .order_by(models.Voucher.voucher_date.desc(), models.Voucher.id.desc())
        .offset(skip).limit(limit).all()
    )
    
    results = []
    for ln in lines:
        results.append({
            "id": ln.id,
            "voucher_id": ln.voucher.id,
            "voucher_type": ln.voucher.voucher_type,
            "voucher_number": ln.voucher.number,
            "voucher_date": ln.voucher.voucher_date,
            "debit": ln.debit,
            "credit": ln.credit,
            "narration": ln.line_narration or ln.voucher.narration,
            "party_id": ln.party_id,
            "party_name": ln.party.name if getattr(ln, 'party', None) else None
        })
    return {"items": results}

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

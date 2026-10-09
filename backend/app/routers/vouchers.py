from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/vouchers", tags=["vouchers"])


@router.post("/", response_model=schemas.VoucherOut)
def create_voucher(
    voucher: schemas.VoucherCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify double entry
    total_debit = sum(line.debit for line in voucher.lines)
    total_credit = sum(line.credit for line in voucher.lines)

    if abs(total_debit - total_credit) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Voucher does not balance. Dr: {total_debit}, Cr: {total_credit}"
        )

    if total_debit <= 0 and total_credit <= 0:
        raise HTTPException(
            status_code=400,
            detail="Voucher must have at least one debit and one credit."
        )

    # Check for empty date, auto-assign
    if not voucher.voucher_date:
        voucher.voucher_date = datetime.now(timezone.utc)

    # Create Voucher
    db_voucher = models.Voucher(
        voucher_type=voucher.voucher_type,
        series=voucher.series,
        number=voucher.number,
        voucher_date=voucher.voucher_date,
        fy=voucher.fy,
        narration=voucher.narration,
        ref_voucher_id=voucher.ref_voucher_id,
        status=voucher.status,
        created_by=current_user.id,
        source=voucher.source,
        source_ref=voucher.source_ref,
    )

    if voucher.status == "POSTED":
        db_voucher.posted_at = datetime.now(timezone.utc)

    db.add(db_voucher)
    db.flush()  # to get db_voucher.id

    for line in voucher.lines:
        db_line = models.VoucherLine(
            voucher_id=db_voucher.id,
            account_id=line.account_id,
            party_id=line.party_id,
            debit=line.debit,
            credit=line.credit,
            item_id=line.item_id,
            qty=line.qty,
            rate=line.rate,
            tax_code=line.tax_code,
            line_narration=line.line_narration
        )
        db.add(db_line)

    db.commit()
    db.refresh(db_voucher)
    return db_voucher


@router.get("/", response_model=schemas.PaginatedResponse[schemas.VoucherOut])
def list_vouchers(
    skip: int = 0,
    limit: int = 50,
    voucher_type: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(models.Voucher)
    if voucher_type:
        query = query.filter(models.Voucher.voucher_type == voucher_type)
    
    total = query.count()
    vouchers = query.order_by(models.Voucher.voucher_date.desc(), models.Voucher.id.desc()).offset(skip).limit(limit).all()
    
    return {
        "items": vouchers,
        "total": total,
        "skip": skip,
        "limit": limit
    }

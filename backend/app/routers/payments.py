from decimal import Decimal
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/payments", tags=["payments"])

@router.get("/", response_model=List[schemas.PaymentOut])
def list_payments(
    party_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(models.Payment)
        .options(joinedload(models.Payment.allocations).joinedload(models.PaymentAllocation.invoice))
        .filter(models.Payment.created_by == current_user.id, models.Payment.is_deleted == False)
    )
    if party_id:
        query = query.filter(models.Payment.party_id == party_id)
    return query.order_by(models.Payment.payment_date.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=schemas.PaymentOut, status_code=201)
def create_payment(
    payload: schemas.PaymentCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify party ownership
    party = (
        db.query(models.Party)
        .filter(models.Party.id == payload.party_id, models.Party.created_by == current_user.id)
        .first()
    )
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    payment = models.Payment(
        party_id=payload.party_id,
        created_by=current_user.id,
        amount=payload.amount,
        unallocated=payload.amount,  # initially all unallocated
        payment_date=payload.payment_date,
        note=payload.note,
        mode=payload.mode,
    )
    db.add(payment)
    db.flush()

    if payload.allocations:
        for alloc in payload.allocations:
            if payment.unallocated < alloc.allocated_amount:
                raise HTTPException(status_code=400, detail="Allocations exceed payment amount")
            
            invoice = db.query(models.Invoice).filter(models.Invoice.id == alloc.invoice_id, models.Invoice.party_id == payload.party_id).first()
            if not invoice:
                raise HTTPException(status_code=404, detail=f"Invoice {alloc.invoice_id} not found")
            if invoice.balance_due < alloc.allocated_amount:
                raise HTTPException(status_code=400, detail=f"Allocation exceeds balance due for invoice {alloc.invoice_id}")
            
            # create allocation record
            payment_alloc = models.PaymentAllocation(
                payment_id=payment.id,
                invoice_id=invoice.id,
                allocated_amount=alloc.allocated_amount
            )
            db.add(payment_alloc)
            
            # adjust balances
            payment.unallocated = Decimal(str(payment.unallocated)) - alloc.allocated_amount
            invoice.balance_due = Decimal(str(invoice.balance_due)) - alloc.allocated_amount
            if invoice.balance_due <= 0:
                invoice.is_paid = True

    db.commit()
    db.refresh(payment)
    return payment


@router.get("/{payment_id}", response_model=schemas.PaymentOut)
def get_payment(
    payment_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payment = (
        db.query(models.Payment)
        .options(joinedload(models.Payment.allocations).joinedload(models.PaymentAllocation.invoice))
        .filter(models.Payment.id == payment_id, models.Payment.created_by == current_user.id, models.Payment.is_deleted == False)
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.post("/{payment_id}/allocate", response_model=schemas.PaymentOut)
def allocate_payment(
    payment_id: int,
    allocations: List[schemas.AllocationCreate],
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payment = (
        db.query(models.Payment)
        .filter(models.Payment.id == payment_id, models.Payment.created_by == current_user.id)
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    for alloc in allocations:
        if payment.unallocated < alloc.allocated_amount:
            raise HTTPException(status_code=400, detail="Allocations exceed remaining unallocated amount")
        
        invoice = db.query(models.Invoice).filter(models.Invoice.id == alloc.invoice_id, models.Invoice.party_id == payment.party_id).first()
        if not invoice:
            raise HTTPException(status_code=404, detail=f"Invoice {alloc.invoice_id} not found")
        if invoice.balance_due < alloc.allocated_amount:
            raise HTTPException(status_code=400, detail=f"Allocation exceeds balance due for invoice {alloc.invoice_id}")
        
        # create allocation record
        payment_alloc = models.PaymentAllocation(
            payment_id=payment.id,
            invoice_id=invoice.id,
            allocated_amount=alloc.allocated_amount
        )
        db.add(payment_alloc)
        
        # adjust balances
        payment.unallocated = Decimal(str(payment.unallocated)) - alloc.allocated_amount
        invoice.balance_due = Decimal(str(invoice.balance_due)) - alloc.allocated_amount
        if invoice.balance_due <= 0:
            invoice.is_paid = True

    db.commit()
    db.refresh(payment)
    return payment

@router.delete("/{payment_id}", status_code=204)
def delete_payment(
    payment_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from decimal import Decimal
    payment = (
        db.query(models.Payment)
        .filter(models.Payment.id == payment_id, models.Payment.created_by == current_user.id, models.Payment.is_deleted == False)
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
        
    payment.is_deleted = True
    
    # Recalibrate: Unallocate from all invoices
    allocations = db.query(models.PaymentAllocation).filter(models.PaymentAllocation.payment_id == payment.id).all()
    for alloc in allocations:
        invoice = db.query(models.Invoice).filter(models.Invoice.id == alloc.invoice_id).first()
        if invoice:
            invoice.balance_due = Decimal(str(invoice.balance_due)) + Decimal(str(alloc.allocated_amount))
            invoice.is_paid = (invoice.balance_due <= 0)
        db.delete(alloc)
        
    db.commit()
    return None


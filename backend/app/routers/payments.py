from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/", response_model=schemas.PaginatedResponse[schemas.PaymentOut])
def list_payments(
    party_id: int | None = None,
    search: str = "",
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Single aggregate query for count + sum, then separate paginated rows query.
    # Removed joinedload(allocations) from the list endpoint — loading the full
    # allocation graph for every payment in a list is extremely wasteful.
    # Allocations are only eagerly loaded on the detail (GET /{payment_id}) endpoint.
    agg_query = (
        db.query(
            func.count(models.Payment.id).label("total"),
            func.coalesce(func.sum(models.Payment.amount), Decimal("0")).label("summary_total"),
        )
        .filter(models.Payment.is_deleted == False)
    )

    if party_id:
        agg_query = agg_query.filter(models.Payment.party_id == party_id)
    if search:
        agg_query = agg_query.join(models.Party).filter(
            models.Party.name.ilike(f"%{search}%")
        )

    agg = agg_query.one()
    total = agg.total
    summary_total = agg.summary_total

    items_query = (
        db.query(models.Payment)
        .options(joinedload(models.Payment.party))
        .filter(models.Payment.is_deleted == False)
    )

    if party_id:
        items_query = items_query.filter(models.Payment.party_id == party_id)
    if search:
        items_query = items_query.join(models.Party).filter(
            models.Party.name.ilike(f"%{search}%")
        )

    items = items_query.order_by(models.Payment.payment_date.desc()).offset(skip).limit(limit).all()

    return schemas.PaginatedResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        summary_total=summary_total,
    )


@router.post("/", response_model=schemas.PaymentOut, status_code=201)
def create_payment(
    payload: schemas.PaymentCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify party exists
    party = (
        db.query(models.Party)
        .filter(models.Party.id == payload.party_id)
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
        # Bulk-fetch all invoices to allocate to in one query
        invoice_ids = [a.invoice_id for a in payload.allocations]
        invoices_map = {
            inv.id: inv
            for inv in db.query(models.Invoice)
                         .filter(
                             models.Invoice.id.in_(invoice_ids),
                             models.Invoice.party_id == payload.party_id,
                         )
                         .all()
        }

        for alloc in payload.allocations:
            if payment.unallocated < alloc.allocated_amount:
                raise HTTPException(status_code=400, detail="Allocations exceed payment amount")

            invoice = invoices_map.get(alloc.invoice_id)
            if not invoice:
                raise HTTPException(status_code=404, detail=f"Invoice {alloc.invoice_id} not found")
            if invoice.balance_due < alloc.allocated_amount:
                raise HTTPException(
                    status_code=400,
                    detail=f"Allocation exceeds balance due for invoice {alloc.invoice_id}",
                )

            # Create allocation record
            db.add(models.PaymentAllocation(
                payment_id=payment.id,
                invoice_id=invoice.id,
                allocated_amount=alloc.allocated_amount,
            ))

            # Adjust balances
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
        .options(
            joinedload(models.Payment.party),
            joinedload(models.Payment.allocations).joinedload(models.PaymentAllocation.invoice),
        )
        .filter(models.Payment.id == payment_id, models.Payment.is_deleted == False)
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
        .filter(models.Payment.id == payment_id)
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Bulk-fetch all invoices at once
    invoice_ids = [a.invoice_id for a in allocations]
    invoices_map = {
        inv.id: inv
        for inv in db.query(models.Invoice)
                     .filter(
                         models.Invoice.id.in_(invoice_ids),
                         models.Invoice.party_id == payment.party_id,
                     )
                     .all()
    }

    for alloc in allocations:
        if payment.unallocated < alloc.allocated_amount:
            raise HTTPException(status_code=400, detail="Allocations exceed remaining unallocated amount")

        invoice = invoices_map.get(alloc.invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail=f"Invoice {alloc.invoice_id} not found")
        if invoice.balance_due < alloc.allocated_amount:
            raise HTTPException(
                status_code=400,
                detail=f"Allocation exceeds balance due for invoice {alloc.invoice_id}",
            )

        db.add(models.PaymentAllocation(
            payment_id=payment.id,
            invoice_id=invoice.id,
            allocated_amount=alloc.allocated_amount,
        ))

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
    payment = (
        db.query(models.Payment)
        .filter(models.Payment.id == payment_id, models.Payment.is_deleted == False)
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    payment.is_deleted = True

    # Recalibrate: fetch all allocations, then bulk-fetch all affected invoices in ONE IN query
    allocations = (
        db.query(models.PaymentAllocation)
        .filter(models.PaymentAllocation.payment_id == payment.id)
        .all()
    )

    if allocations:
        invoice_ids = [a.invoice_id for a in allocations]
        invoices_map = {
            inv.id: inv
            for inv in db.query(models.Invoice)
                         .filter(models.Invoice.id.in_(invoice_ids))
                         .all()
        }

        for alloc in allocations:
            invoice = invoices_map.get(alloc.invoice_id)
            if invoice:
                invoice.balance_due = Decimal(str(invoice.balance_due)) + Decimal(str(alloc.allocated_amount))
                invoice.is_paid = (invoice.balance_due <= 0)
            db.delete(alloc)

    db.commit()
    return None

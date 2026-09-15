from datetime import datetime, timezone
from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..gcs import upload_file_to_gcs

router = APIRouter(prefix="/invoices", tags=["invoices"])


def _next_invoice_number(user_id: int, db: Session) -> str:
    count = db.query(models.Invoice).filter(models.Invoice.created_by == user_id).count()
    return f"INV-{count + 1:05d}"


@router.post("/upload")
def upload_challan(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user)
):
    try:
        url = upload_file_to_gcs(file.file, file.filename, file.content_type)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=schemas.PaginatedResponse[schemas.InvoiceOut])
def list_invoices(
    party_id: int | None = None,
    unpaid_only: bool = False,
    search: str = "",
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(models.Invoice).options(joinedload(models.Invoice.party)).filter(models.Invoice.is_deleted == False)
    if party_id:
        query = query.filter(models.Invoice.party_id == party_id)
    if unpaid_only:
        query = query.filter(models.Invoice.is_paid == False)
    if search:
        # Search by invoice number or party name
        query = query.join(models.Party).filter(
            (models.Invoice.invoice_number.ilike(f"%{search}%")) |
            (models.Party.name.ilike(f"%{search}%"))
        )
        
    total = query.count()
    
    # Calculate summary total for the current filtered query
    # Need a separate query for func.sum to avoid counting issues with joinedload
    sum_query = db.query(func.sum(models.Invoice.amount)).filter(models.Invoice.is_deleted == False)
    if party_id:
        sum_query = sum_query.filter(models.Invoice.party_id == party_id)
    if unpaid_only:
        sum_query = sum_query.filter(models.Invoice.is_paid == False)
    if search:
        sum_query = sum_query.join(models.Party).filter(
            (models.Invoice.invoice_number.ilike(f"%{search}%")) |
            (models.Party.name.ilike(f"%{search}%"))
        )
    summary_total = sum_query.scalar() or Decimal("0")

    items = query.order_by(models.Invoice.invoice_date.desc()).offset(skip).limit(limit).all()
    
    return schemas.PaginatedResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        summary_total=summary_total
    )


@router.post("/", response_model=schemas.InvoiceOut, status_code=201)
def create_invoice(
    payload: schemas.InvoiceCreate,
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

    invoice_number = payload.invoice_number or _next_invoice_number(current_user.id, db)

    # Check duplicate invoice number globally
    existing = (
        db.query(models.Invoice)
        .filter(
            models.Invoice.invoice_number == invoice_number,
            models.Invoice.is_deleted == False,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Invoice number {invoice_number!r} already exists")

    # Calculate total amount from items
    total_amount = sum((item.meter * item.rate) for item in payload.items)

    invoice = models.Invoice(
        invoice_number=invoice_number,
        party_id=payload.party_id,
        created_by=current_user.id,
        amount=total_amount,
        balance_due=total_amount,   # starts fully unpaid
        billing_address=payload.billing_address,
        shipping_address=payload.shipping_address,
        description=payload.description,
        invoice_date=payload.invoice_date,
        due_date=payload.due_date,
    )
    db.add(invoice)
    db.flush()  # get invoice.id

    for item in payload.items:
        db_item = models.InvoiceItem(
            invoice_id=invoice.id,
            item_name=item.item_name,
            meter=item.meter,
            rate=item.rate,
            total=item.meter * item.rate
        )
        db.add(db_item)

    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/{invoice_id}", response_model=schemas.InvoiceOut)
def get_invoice(
    invoice_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    inv = (
        db.query(models.Invoice)
        .filter(models.Invoice.id == invoice_id, models.Invoice.is_deleted == False)
        .first()
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return inv


@router.put("/{invoice_id}", response_model=schemas.InvoiceOut)
def update_invoice(
    invoice_id: int,
    payload: schemas.InvoiceUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from decimal import Decimal
    inv = (
        db.query(models.Invoice)
        .filter(models.Invoice.id == invoice_id, models.Invoice.is_deleted == False)
        .first()
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    update_data = payload.model_dump(exclude_unset=True)
    
    # Handle item modifications and recalibration
    if "items" in update_data:
        items_data = update_data.pop("items")
        
        # Calculate new total amount
        new_amount = sum((Decimal(str(item["meter"])) * Decimal(str(item["rate"]))) for item in items_data)
        old_amount = Decimal(str(inv.amount))
        diff = new_amount - old_amount
        
        if diff != 0:
            # Reconstruct items
            db.query(models.InvoiceItem).filter(models.InvoiceItem.invoice_id == inv.id).delete()
            for item in items_data:
                db_item = models.InvoiceItem(
                    invoice_id=inv.id,
                    item_name=item["item_name"],
                    meter=item["meter"],
                    rate=item["rate"],
                    total=Decimal(str(item["meter"])) * Decimal(str(item["rate"]))
                )
                db.add(db_item)
                
            inv.amount = new_amount
            
            if diff > 0:
                inv.balance_due = Decimal(str(inv.balance_due)) + diff
            else:
                # diff < 0. Amount decreased.
                # If balance_due + diff < 0, it means the invoice is now overpaid.
                new_balance = Decimal(str(inv.balance_due)) + diff
                if new_balance < 0:
                    overpaid_amount = abs(new_balance)
                    
                    # We must unallocate `overpaid_amount` from existing allocations for this invoice.
                    allocations = db.query(models.PaymentAllocation).filter(models.PaymentAllocation.invoice_id == inv.id).all()
                    
                    for alloc in allocations:
                        if overpaid_amount <= 0:
                            break
                        
                        to_unallocate = min(overpaid_amount, Decimal(str(alloc.allocated_amount)))
                        alloc.allocated_amount = Decimal(str(alloc.allocated_amount)) - to_unallocate
                        
                        # Return money to the payment's unallocated pool
                        payment = db.query(models.Payment).filter(models.Payment.id == alloc.payment_id).first()
                        if payment:
                            payment.unallocated = Decimal(str(payment.unallocated)) + to_unallocate
                            
                        overpaid_amount -= to_unallocate
                        
                        if alloc.allocated_amount == 0:
                            db.delete(alloc)
                            
                    inv.balance_due = Decimal("0")
                else:
                    inv.balance_due = new_balance
                    
            inv.is_paid = (inv.balance_due <= 0)

    # Update other fields
    for field, value in update_data.items():
        setattr(inv, field, value)
        
    db.commit()
    db.refresh(inv)
    return inv


@router.delete("/{invoice_id}", status_code=204)
def delete_invoice(
    invoice_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from decimal import Decimal
    inv = (
        db.query(models.Invoice)
        .filter(models.Invoice.id == invoice_id, models.Invoice.is_deleted == False)
        .first()
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    inv.is_deleted = True
    
    # Recalibrate: Unallocate all payments
    allocations = db.query(models.PaymentAllocation).filter(models.PaymentAllocation.invoice_id == inv.id).all()
    for alloc in allocations:
        payment = db.query(models.Payment).filter(models.Payment.id == alloc.payment_id).first()
        if payment:
            payment.unallocated = Decimal(str(payment.unallocated)) + Decimal(str(alloc.allocated_amount))
        db.delete(alloc)
        
    db.commit()
    return None

from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/invoices", tags=["invoices"])


def _next_invoice_number(user_id: int, db: Session) -> str:
    count = db.query(models.Invoice).filter(models.Invoice.created_by == user_id).count()
    return f"INV-{count + 1:05d}"


@router.get("/", response_model=List[schemas.InvoiceOut])
def list_invoices(
    party_id: int | None = None,
    unpaid_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(models.Invoice).filter(models.Invoice.created_by == current_user.id)
    if party_id:
        query = query.filter(models.Invoice.party_id == party_id)
    if unpaid_only:
        query = query.filter(models.Invoice.is_paid == False)
    return query.order_by(models.Invoice.invoice_date.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=schemas.InvoiceOut, status_code=201)
def create_invoice(
    payload: schemas.InvoiceCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify party belongs to user
    party = (
        db.query(models.Party)
        .filter(models.Party.id == payload.party_id, models.Party.created_by == current_user.id)
        .first()
    )
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    invoice_number = payload.invoice_number or _next_invoice_number(current_user.id, db)

    # Check duplicate invoice number for this user
    existing = (
        db.query(models.Invoice)
        .filter(
            models.Invoice.invoice_number == invoice_number,
            models.Invoice.created_by == current_user.id,
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
        .filter(models.Invoice.id == invoice_id, models.Invoice.created_by == current_user.id)
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
    inv = (
        db.query(models.Invoice)
        .filter(models.Invoice.id == invoice_id, models.Invoice.created_by == current_user.id)
        .first()
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(inv, field, value)
    db.commit()
    db.refresh(inv)
    return inv

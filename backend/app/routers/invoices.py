from datetime import datetime, timezone
from typing import List, Optional

from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, text

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..gcs import upload_file_to_gcs

router = APIRouter(prefix="/invoices", tags=["invoices"])


def _current_fy() -> tuple[int, int]:
    """Return (fy_start_year, fy_end_year) based on today. FY starts April 1."""
    today = datetime.now(timezone.utc)
    if today.month >= 4:
        return today.year, today.year + 1
    return today.year - 1, today.year


def _next_invoice_number(user_id: int, db: Session) -> str:
    """F3: FY-scoped invoice number with prefix INV/YY-YY/NNNN."""
    fy_start, fy_end = _current_fy()
    fy_start_dt = datetime(fy_start, 4, 1, tzinfo=timezone.utc)
    fy_end_dt   = datetime(fy_end,   4, 1, tzinfo=timezone.utc)
    prefix = f"INV/{str(fy_start)[2:]}-{str(fy_end)[2:]}/"

    count = db.execute(
        text("SELECT COUNT(*) FROM invoices WHERE invoice_date >= :s AND invoice_date < :e"),
        {"s": fy_start_dt, "e": fy_end_dt},
    ).scalar() or 0
    return f"{prefix}{count + 1:04d}"


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
    agent_name: str | None = None,
    from_date: Optional[str] = None,   # F4: ISO date string
    to_date: Optional[str] = None,     # F4: ISO date string
    min_amount: Optional[float] = None, # F19
    max_amount: Optional[float] = None, # F19
    skip: int = 0,
    limit: int = 1000000,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Build base filter — single query for both count+sum using func aggregates,
    # then a second paginated query for the actual rows with eager-loaded relations.
    query = (
        db.query(
            func.count(models.Invoice.id).label("total"),
            func.coalesce(func.sum(models.Invoice.amount), Decimal("0")).label("summary_total"),
        )
        .filter(models.Invoice.is_deleted == False)
    )

    if party_id:
        query = query.filter(models.Invoice.party_id == party_id)
    if unpaid_only:
        query = query.filter(models.Invoice.is_paid == False)
    
    if search or agent_name:
        query = query.join(models.Party)
        
    if search:
        query = query.filter(
            (models.Invoice.invoice_number.ilike(f"%{search}%")) |
            (models.Party.name.ilike(f"%{search}%"))
        )
    if agent_name:
        query = query.filter(models.Party.agent == agent_name)

    # F4: date filters
    if from_date:
        query = query.filter(models.Invoice.invoice_date >= datetime.fromisoformat(from_date))
    if to_date:
        query = query.filter(models.Invoice.invoice_date <= datetime.fromisoformat(to_date))
    # F19: amount filters
    if min_amount is not None:
        query = query.filter(models.Invoice.amount >= min_amount)
    if max_amount is not None:
        query = query.filter(models.Invoice.amount <= max_amount)

    agg = query.one()
    total = agg.total
    summary_total = agg.summary_total

    # Paginated rows with joined relations
    items_query = (
        db.query(models.Invoice)
        .options(
            joinedload(models.Invoice.party),
            joinedload(models.Invoice.items),
        )
        .filter(models.Invoice.is_deleted == False)
    )

    if party_id:
        items_query = items_query.filter(models.Invoice.party_id == party_id)
    if unpaid_only:
        items_query = items_query.filter(models.Invoice.is_paid == False)
    
    if search or agent_name:
        items_query = items_query.join(models.Party)
        
    if search:
        items_query = items_query.filter(
            (models.Invoice.invoice_number.ilike(f"%{search}%")) |
            (models.Party.name.ilike(f"%{search}%"))
        )
    if agent_name:
        items_query = items_query.filter(models.Party.agent == agent_name)

    # F4: date filters on items query
    if from_date:
        items_query = items_query.filter(models.Invoice.invoice_date >= datetime.fromisoformat(from_date))
    if to_date:
        items_query = items_query.filter(models.Invoice.invoice_date <= datetime.fromisoformat(to_date))
    # F19: amount filters on items query
    if min_amount is not None:
        items_query = items_query.filter(models.Invoice.amount >= min_amount)
    if max_amount is not None:
        items_query = items_query.filter(models.Invoice.amount <= max_amount)

    items = items_query.order_by(models.Invoice.invoice_date.desc()).offset(skip).limit(limit).all()

    return schemas.PaginatedResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        summary_total=summary_total,
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
        .options(joinedload(models.Invoice.party), joinedload(models.Invoice.items))
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
                # diff < 0 — amount decreased
                new_balance = Decimal(str(inv.balance_due)) + diff
                if new_balance < 0:
                    overpaid_amount = abs(new_balance)

                    allocations = (
                        db.query(models.PaymentAllocation)
                        .filter(models.PaymentAllocation.invoice_id == inv.id)
                        .all()
                    )

                    # Bulk-fetch all payments for these allocations in ONE query
                    payment_ids = [a.payment_id for a in allocations]
                    payments_map = {}
                    if payment_ids:
                        payments_map = {
                            p.id: p
                            for p in db.query(models.Payment)
                                       .filter(models.Payment.id.in_(payment_ids))
                                       .all()
                        }

                    for alloc in allocations:
                        if overpaid_amount <= 0:
                            break

                        to_unallocate = min(overpaid_amount, Decimal(str(alloc.allocated_amount)))
                        alloc.allocated_amount = Decimal(str(alloc.allocated_amount)) - to_unallocate

                        payment = payments_map.get(alloc.payment_id)
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
    inv = (
        db.query(models.Invoice)
        .filter(models.Invoice.id == invoice_id, models.Invoice.is_deleted == False)
        .first()
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    inv.is_deleted = True

    # Recalibrate: fetch all allocations, then bulk-fetch all payments in one IN query
    allocations = (
        db.query(models.PaymentAllocation)
        .filter(models.PaymentAllocation.invoice_id == inv.id)
        .all()
    )

    if allocations:
        payment_ids = [a.payment_id for a in allocations]
        payments_map = {
            p.id: p
            for p in db.query(models.Payment)
                       .filter(models.Payment.id.in_(payment_ids))
                       .all()
        }

        for alloc in allocations:
            payment = payments_map.get(alloc.payment_id)
            if payment:
                payment.unallocated = Decimal(str(payment.unallocated)) + Decimal(str(alloc.allocated_amount))
            db.delete(alloc)

    db.commit()
    return None

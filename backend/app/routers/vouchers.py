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

    # Enforce period lock
    from .settings import get_period_lock_date
    lock_date = get_period_lock_date(db)
    if lock_date and voucher.voucher_date.replace(tzinfo=None) <= lock_date:
        raise HTTPException(
            status_code=403,
            detail=f"Cannot post voucher. Books are closed on or before {lock_date.strftime('%d-%m-%Y')}."
        )

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

    import json
    audit = models.AuditLog(
        entity="Voucher",
        entity_id=db_voucher.id,
        action="CREATE",
        after_json=json.dumps({"voucher_type": voucher.voucher_type, "total_dr": float(total_debit), "total_cr": float(total_credit)}),
        user_id=current_user.id
    )
    db.add(audit)

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

@router.post("/{voucher_id}/reverse", response_model=schemas.VoucherOut)
def reverse_voucher(
    voucher_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    orig = db.query(models.Voucher).filter(models.Voucher.id == voucher_id).first()
    if not orig:
        raise HTTPException(404, "Voucher not found")
    if orig.status == "REVERSED":
        raise HTTPException(400, "Voucher is already reversed")
    if orig.status == "CANCELLED":
        raise HTTPException(400, "Voucher is cancelled")

    from .settings import get_period_lock_date
    lock_date = get_period_lock_date(db)
    now_date = datetime.now(timezone.utc)
    if lock_date and now_date.replace(tzinfo=None) <= lock_date:
        raise HTTPException(
            status_code=403,
            detail=f"Cannot reverse voucher. Books are closed on or before {lock_date.strftime('%d-%m-%Y')}."
        )

    # Create reversal voucher
    rev = models.Voucher(
        voucher_type=orig.voucher_type,
        voucher_date=datetime.now(timezone.utc),
        narration=f"Reversal of {orig.voucher_type} #{orig.number or orig.id}",
        ref_voucher_id=orig.id,
        status="POSTED",
        created_by=current_user.id,
        posted_at=datetime.now(timezone.utc)
    )
    db.add(rev)
    db.flush()

    # Reverse lines
    for ln in orig.lines:
        rev_line = models.VoucherLine(
            voucher_id=rev.id,
            account_id=ln.account_id,
            party_id=ln.party_id,
            debit=ln.credit,   # Swap Dr/Cr
            credit=ln.debit,
            item_id=ln.item_id,
            qty=ln.qty,
            rate=ln.rate,
            tax_code=ln.tax_code,
            line_narration=f"Reversal of line {ln.id}"
        )
        db.add(rev_line)

    orig.status = "REVERSED"
    orig.reversed_by_voucher_id = rev.id
    
    import json
    audit_orig = models.AuditLog(
        entity="Voucher",
        entity_id=orig.id,
        action="REVERSE",
        before_json=json.dumps({"status": "POSTED"}),
        after_json=json.dumps({"status": "REVERSED", "reversed_by_voucher_id": rev.id}),
        user_id=current_user.id
    )
    db.add(audit_orig)

    audit_rev = models.AuditLog(
        entity="Voucher",
        entity_id=rev.id,
        action="CREATE_REVERSAL",
        after_json=json.dumps({"voucher_type": rev.voucher_type, "ref_voucher_id": orig.id}),
        user_id=current_user.id
    )
    db.add(audit_rev)

    db.commit()
    db.refresh(rev)
    return rev

@router.get("/{voucher_id}/history")
def get_voucher_history(
    voucher_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logs = db.query(models.AuditLog).filter(
        models.AuditLog.entity == "Voucher",
        models.AuditLog.entity_id == voucher_id
    ).order_by(models.AuditLog.created_at.desc()).all()
    
    result = []
    for l in logs:
        result.append({
            "id": l.id,
            "action": l.action,
            "before_json": l.before_json,
            "after_json": l.after_json,
            "created_at": l.created_at,
            "user_id": l.user_id,
            "username": l.user.username if l.user else "Unknown"
        })
    return result
@router.post("/sales-return", response_model=schemas.VoucherOut)
def create_sales_return(
    payload: dict, # expecting party_id, invoice_id, amount, reason
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from decimal import Decimal
    from datetime import datetime, timezone
    
    party_id = payload.get("party_id")
    invoice_id = payload.get("invoice_id")
    amount = Decimal(str(payload.get("amount", 0)))
    reason = payload.get("reason", "Sales Return")
    
    if amount <= 0:
        raise HTTPException(400, "Invalid amount")
    if not party_id:
        raise HTTPException(400, "Party is required")
        
    party = db.query(models.Party).filter(models.Party.id == party_id).first()
    if not party:
        raise HTTPException(404, "Party not found")
        
    invoice = None
    if invoice_id:
        invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
        if not invoice:
            raise HTTPException(404, "Invoice not found")
        if invoice.balance_due < amount:
            raise HTTPException(400, "Return amount cannot exceed invoice balance due. Or use On-Account settlement.")
            
    # Find Accounts
    sales_return_acc = db.query(models.Account).filter(models.Account.name.ilike("%return%")).first()
    if not sales_return_acc:
        # Fallback to Sales account
        sales_return_acc = db.query(models.Account).filter(models.Account.name.ilike("%sales%")).first()
        
    party_acc = db.query(models.Account).filter(models.Account.is_party_control == True, models.Account.code == "DEBTORS").first()
    if not party_acc:
        party_acc = db.query(models.Account).filter(models.Account.is_party_control == True).first()
        
    if not sales_return_acc or not party_acc:
        raise HTTPException(500, "Required accounts not found. Please setup Chart of Accounts.")

    # 1. Create Voucher
    from .invoices import _next_invoice_number # We can use a similar logic, but for now just timestamp
    import time
    
    voucher = models.Voucher(
        voucher_type="CREDIT_NOTE",
        voucher_date=datetime.now(timezone.utc),
        narration=reason,
        source="INVOICE" if invoice else None,
        source_ref=str(invoice.id) if invoice else None,
        status="POSTED",
        created_by=current_user.id,
        posted_at=datetime.now(timezone.utc)
    )
    db.add(voucher)
    db.flush()
    
    # 2. Add Voucher Lines
    # Dr. Sales Return
    db.add(models.VoucherLine(
        voucher_id=voucher.id,
        account_id=sales_return_acc.id,
        debit=amount,
        credit=0,
        line_narration=reason
    ))
    
    # Cr. Party
    db.add(models.VoucherLine(
        voucher_id=voucher.id,
        account_id=party_acc.id,
        party_id=party.id,
        debit=0,
        credit=amount,
        line_narration=reason
    ))
    
    # 3. Handle Settlement
    if invoice:
        # Reduce invoice balance
        invoice.balance_due = Decimal(str(invoice.balance_due)) - amount
        if invoice.balance_due <= 0:
            invoice.is_paid = True
            
        # Record the allocation
        db.add(models.PaymentAllocation(
            voucher_id=voucher.id,
            invoice_id=invoice.id,
            allocated_amount=amount
        ))
    else:
        # On-account credit note? We would need to create a Payment with unallocated amount
        # so it shows up in "Advance / On Account".
        # A Credit Note conceptually acts as a receipt without money.
        payment = models.Payment(
            party_id=party.id,
            amount=0,
            unallocated=amount, # This puts it into the party's advance pool
            payment_date=datetime.now(timezone.utc),
            note=f"Credit Note: {reason}",
            mode="ADJUSTMENT",
            created_by=current_user.id
        )
        db.add(payment)
        
    db.commit()
    db.refresh(voucher)
    return voucher

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=schemas.DashboardSummary)
def dashboard_summary(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    total_parties = db.query(models.Party).filter(models.Party.is_active == True).count()
    invoices_count = db.query(models.Invoice).filter(models.Invoice.is_deleted == False).count()
    
    total_invoiced = db.query(func.sum(models.Invoice.amount)).filter(models.Invoice.is_deleted == False).scalar() or Decimal("0")
    total_collected = db.query(func.sum(models.Payment.amount)).filter(models.Payment.is_deleted == False).scalar() or Decimal("0")
    total_journal = db.query(func.sum(models.JournalEntry.amount)).filter(models.JournalEntry.is_deleted == False).scalar() or Decimal("0")
    
    total_outstanding = total_invoiced + total_journal - total_collected

    overdue_count = db.query(models.Invoice).filter(
        models.Invoice.is_deleted == False,
        models.Invoice.is_paid == False,
        models.Invoice.due_date < now
    ).count()

    payments = (
        db.query(models.Payment)
        .filter(models.Payment.is_deleted == False)
        .order_by(models.Payment.payment_date.desc())
        .limit(5)
        .all()
    )

    return schemas.DashboardSummary(
        total_parties=total_parties,
        total_invoiced=total_invoiced,
        total_collected=total_collected,
        total_journal=total_journal,
        total_outstanding=total_outstanding,
        invoices_count=invoices_count,
        overdue_count=overdue_count,
        recent_payments=payments,
    )


@router.get("/parties", response_model=List[schemas.PartySummary])
def party_summaries(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    inv_sub = db.query(func.coalesce(func.sum(models.Invoice.amount), Decimal("0")))\
        .filter(models.Invoice.party_id == models.Party.id, models.Invoice.is_deleted == False).scalar_subquery()
    pmt_sub = db.query(func.coalesce(func.sum(models.Payment.amount), Decimal("0")))\
        .filter(models.Payment.party_id == models.Party.id, models.Payment.is_deleted == False).scalar_subquery()
    jnl_sub = db.query(func.coalesce(func.sum(models.JournalEntry.amount), Decimal("0")))\
        .filter(models.JournalEntry.party_id == models.Party.id, models.JournalEntry.is_deleted == False).scalar_subquery()
    
    inv_count_sub = db.query(func.count(models.Invoice.id))\
        .filter(models.Invoice.party_id == models.Party.id, models.Invoice.is_deleted == False).scalar_subquery()
    pmt_count_sub = db.query(func.count(models.Payment.id))\
        .filter(models.Payment.party_id == models.Party.id, models.Payment.is_deleted == False).scalar_subquery()

    rows = db.query(
        models.Party,
        inv_sub.label("inv"),
        pmt_sub.label("pmt"),
        jnl_sub.label("jnl"),
        inv_count_sub.label("inv_c"),
        pmt_count_sub.label("pmt_c")
    ).filter(models.Party.is_active == True).all()

    result = []
    for party, inv, pmt, jnl, inv_c, pmt_c in rows:
        outstanding = inv + jnl - pmt
        result.append(
            schemas.PartySummary(
                party_id=party.id,
                party_name=party.name,
                total_invoiced=inv,
                total_paid=pmt,
                total_journal=jnl,
                outstanding=outstanding,
                invoice_count=inv_c,
                payment_count=pmt_c,
            )
        )
    # Sort by outstanding desc (top debtors first)
    result.sort(key=lambda x: x.outstanding, reverse=True)
    return result


@router.get("/party/{party_id}", response_model=schemas.PartySummary)
def party_analytics(
    party_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    inv_sub = db.query(func.coalesce(func.sum(models.Invoice.amount), Decimal("0")))\
        .filter(models.Invoice.party_id == models.Party.id, models.Invoice.is_deleted == False).scalar_subquery()
    pmt_sub = db.query(func.coalesce(func.sum(models.Payment.amount), Decimal("0")))\
        .filter(models.Payment.party_id == models.Party.id, models.Payment.is_deleted == False).scalar_subquery()
    jnl_sub = db.query(func.coalesce(func.sum(models.JournalEntry.amount), Decimal("0")))\
        .filter(models.JournalEntry.party_id == models.Party.id, models.JournalEntry.is_deleted == False).scalar_subquery()
    
    inv_count_sub = db.query(func.count(models.Invoice.id))\
        .filter(models.Invoice.party_id == models.Party.id, models.Invoice.is_deleted == False).scalar_subquery()
    pmt_count_sub = db.query(func.count(models.Payment.id))\
        .filter(models.Payment.party_id == models.Party.id, models.Payment.is_deleted == False).scalar_subquery()

    row = db.query(
        models.Party,
        inv_sub.label("inv"),
        pmt_sub.label("pmt"),
        jnl_sub.label("jnl"),
        inv_count_sub.label("inv_c"),
        pmt_count_sub.label("pmt_c")
    ).filter(models.Party.id == party_id).first()

    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Party not found")

    party, inv, pmt, jnl, inv_c, pmt_c = row
    outstanding = inv + jnl - pmt
    return schemas.PartySummary(
        party_id=party.id,
        party_name=party.name,
        total_invoiced=inv,
        total_paid=pmt,
        total_journal=jnl,
        outstanding=outstanding,
        invoice_count=inv_c,
        payment_count=pmt_c,
    )


@router.get("/aging", response_model=List[schemas.AgingBucket])
def aging_report(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    
    invoices = db.query(models.Invoice, models.Party).join(
        models.Party, models.Invoice.party_id == models.Party.id
    ).filter(
        models.Party.is_active == True,
        models.Invoice.is_deleted == False,
        models.Invoice.is_paid == False,
        models.Invoice.balance_due > 0
    ).all()

    party_buckets = {}
    for inv, party in invoices:
        if party.id not in party_buckets:
            party_buckets[party.id] = {
                "party_id": party.id,
                "party_name": party.name,
                "current": Decimal("0"),
                "days_31_60": Decimal("0"),
                "days_61_90": Decimal("0"),
                "over_90": Decimal("0")
            }
            
        ref_date = (inv.due_date or inv.invoice_date).replace(tzinfo=timezone.utc)
        age_days = (now - ref_date).days
        
        if age_days <= 30:
            party_buckets[party.id]["current"] += inv.balance_due
        elif age_days <= 60:
            party_buckets[party.id]["days_31_60"] += inv.balance_due
        elif age_days <= 90:
            party_buckets[party.id]["days_61_90"] += inv.balance_due
        else:
            party_buckets[party.id]["over_90"] += inv.balance_due

    result = []
    for buckets in party_buckets.values():
        total = buckets["current"] + buckets["days_31_60"] + buckets["days_61_90"] + buckets["over_90"]
        if total > 0:
            result.append(schemas.AgingBucket(total=total, **buckets))

    result.sort(key=lambda x: x.total, reverse=True)
    return result

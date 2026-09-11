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

    parties = db.query(models.Party).filter(
        models.Party.is_active == True,
    ).all()

    invoices = db.query(models.Invoice).all()

    payments = (
        db.query(models.Payment)
        .order_by(models.Payment.payment_date.desc())
        .limit(5)
        .all()
    )

    total_invoiced = sum(i.amount for i in invoices) or Decimal("0")
    total_collected = sum(p.amount for p in db.query(models.Payment).all()) or Decimal("0")
    total_outstanding = total_invoiced - total_collected

    overdue = sum(
        1 for i in invoices
        if not i.is_paid and i.due_date and i.due_date.replace(tzinfo=timezone.utc) < now
    )

    return schemas.DashboardSummary(
        total_parties=len(parties),
        total_invoiced=total_invoiced,
        total_collected=total_collected,
        total_outstanding=total_outstanding,
        invoices_count=len(invoices),
        overdue_count=overdue,
        recent_payments=payments,
    )


@router.get("/parties", response_model=List[schemas.PartySummary])
def party_summaries(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    parties = db.query(models.Party).filter(
        models.Party.is_active == True,
    ).all()

    result = []
    for p in parties:
        total_invoiced = sum(i.amount for i in p.invoices) or Decimal("0")
        total_paid = sum(pay.amount for pay in p.payments) or Decimal("0")
        result.append(
            schemas.PartySummary(
                party_id=p.id,
                party_name=p.name,
                total_invoiced=total_invoiced,
                total_paid=total_paid,
                outstanding=total_invoiced - total_paid,
                invoice_count=len(p.invoices),
                payment_count=len(p.payments),
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
    p = (
        db.query(models.Party)
        .filter(models.Party.id == party_id)
        .first()
    )
    if not p:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Party not found")

    total_invoiced = sum(i.amount for i in p.invoices) or Decimal("0")
    total_paid = sum(pay.amount for pay in p.payments) or Decimal("0")
    return schemas.PartySummary(
        party_id=p.id,
        party_name=p.name,
        total_invoiced=total_invoiced,
        total_paid=total_paid,
        outstanding=total_invoiced - total_paid,
        invoice_count=len(p.invoices),
        payment_count=len(p.payments),
    )


@router.get("/aging", response_model=List[schemas.AgingBucket])
def aging_report(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    parties = db.query(models.Party).filter(
        models.Party.is_active == True,
    ).all()

    result = []
    for p in parties:
        buckets = {"current": Decimal("0"), "days_31_60": Decimal("0"),
                   "days_61_90": Decimal("0"), "over_90": Decimal("0")}
        for inv in p.invoices:
            if inv.is_paid:
                continue
            ref_date = (inv.due_date or inv.invoice_date).replace(tzinfo=timezone.utc)
            age_days = (now - ref_date).days
            if age_days <= 30:
                buckets["current"] += inv.balance_due
            elif age_days <= 60:
                buckets["days_31_60"] += inv.balance_due
            elif age_days <= 90:
                buckets["days_61_90"] += inv.balance_due
            else:
                buckets["over_90"] += inv.balance_due

        total = sum(buckets.values())
        if total > 0:
            result.append(schemas.AgingBucket(party_id=p.id, party_name=p.name, total=total, **buckets))

    result.sort(key=lambda x: x.total, reverse=True)
    return result

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


@router.get("/parties", response_model=schemas.PaginatedResponse[schemas.PartySummary])
def party_summaries(
    skip: int = 0,
    limit: int = 100,
    search: str = "",
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

    base_query = db.query(models.Party).filter(models.Party.is_active == True)
    if search:
        base_query = base_query.filter(models.Party.name.ilike(f"%{search}%"))
        
    total = base_query.count()

    query = db.query(
        models.Party,
        inv_sub.label("inv"),
        pmt_sub.label("pmt"),
        jnl_sub.label("jnl"),
        inv_count_sub.label("inv_c"),
        pmt_count_sub.label("pmt_c")
    ).filter(models.Party.is_active == True)
    
    if search:
        query = query.filter(models.Party.name.ilike(f"%{search}%"))
        
    # Sort by outstanding desc directly in DB
    outstanding_expr = (inv_sub + jnl_sub - pmt_sub)
    rows = query.order_by(outstanding_expr.desc()).offset(skip).limit(limit).all()

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

    return schemas.PaginatedResponse(
        items=result,
        total=total,
        skip=skip,
        limit=limit
    )


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


@router.get("/aging", response_model=schemas.PaginatedResponse[schemas.AgingBucket])
def aging_report(
    skip: int = 0,
    limit: int = 100,
    search: str = "",
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from sqlalchemy import case
    now = datetime.now(timezone.utc)
    date_30 = now - timedelta(days=30)
    date_60 = now - timedelta(days=60)
    date_90 = now - timedelta(days=90)
    
    ref_date = func.coalesce(models.Invoice.due_date, models.Invoice.invoice_date)
    
    current_expr = func.coalesce(func.sum(case((ref_date >= date_30, models.Invoice.balance_due), else_=Decimal("0"))), Decimal("0"))
    days_31_60_expr = func.coalesce(func.sum(case(((ref_date < date_30) & (ref_date >= date_60), models.Invoice.balance_due), else_=Decimal("0"))), Decimal("0"))
    days_61_90_expr = func.coalesce(func.sum(case(((ref_date < date_60) & (ref_date >= date_90), models.Invoice.balance_due), else_=Decimal("0"))), Decimal("0"))
    over_90_expr = func.coalesce(func.sum(case((ref_date < date_90, models.Invoice.balance_due), else_=Decimal("0"))), Decimal("0"))
    
    total_expr = current_expr + days_31_60_expr + days_61_90_expr + over_90_expr

    base_query = db.query(models.Party).join(
        models.Invoice, models.Invoice.party_id == models.Party.id
    ).filter(
        models.Party.is_active == True,
        models.Invoice.is_deleted == False,
        models.Invoice.is_paid == False,
        models.Invoice.balance_due > 0
    )
    
    if search:
        base_query = base_query.filter(models.Party.name.ilike(f"%{search}%"))
        
    total = base_query.distinct(models.Party.id).count()

    query = db.query(
        models.Party.id,
        models.Party.name,
        current_expr.label("current"),
        days_31_60_expr.label("days_31_60"),
        days_61_90_expr.label("days_61_90"),
        over_90_expr.label("over_90"),
        total_expr.label("total_amount")
    ).join(
        models.Invoice, models.Invoice.party_id == models.Party.id
    ).filter(
        models.Party.is_active == True,
        models.Invoice.is_deleted == False,
        models.Invoice.is_paid == False,
        models.Invoice.balance_due > 0
    )
    
    if search:
        query = query.filter(models.Party.name.ilike(f"%{search}%"))
        
    rows = query.group_by(models.Party.id, models.Party.name).order_by(total_expr.desc()).offset(skip).limit(limit).all()

    result = []
    for pid, pname, curr, d31, d61, o90, tot in rows:
        result.append(schemas.AgingBucket(
            party_id=pid,
            party_name=pname,
            current=curr,
            days_31_60=d31,
            days_61_90=d61,
            over_90=o90,
            total=tot
        ))

    return schemas.PaginatedResponse(
        items=result,
        total=total,
        skip=skip,
        limit=limit
    )

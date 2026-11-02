from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/challans", tags=["challans"])


class ChallanCreate(BaseModel):
    image_url: str
    party_id: Optional[int] = None
    party_name: Optional[str] = None
    challan_number: Optional[str] = None
    notes: Optional[str] = None


class ChallanOut(BaseModel):
    id: int
    challan_number: Optional[str] = None
    party_id: Optional[int] = None
    party_name: Optional[str] = None
    image_url: str
    notes: Optional[str] = None
    status: str
    invoice_id: Optional[int] = None
    invoice_number: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChallanListResponse(BaseModel):
    items: List[ChallanOut]
    total: int
    pending_count: int
    invoiced_count: int


@router.get("/", response_model=ChallanListResponse)
def list_challans(
    status: Optional[str] = "ALL",  # PENDING | INVOICED | ALL
    party_id: Optional[int] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(models.DeliveryChallan)
        .options(
            joinedload(models.DeliveryChallan.party),
            joinedload(models.DeliveryChallan.invoice),
        )
    )

    if status and status.upper() in ("PENDING", "INVOICED"):
        query = query.filter(models.DeliveryChallan.status == status.upper())

    if party_id:
        query = query.filter(models.DeliveryChallan.party_id == party_id)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (models.DeliveryChallan.party_name.ilike(search_pattern))
            | (models.DeliveryChallan.challan_number.ilike(search_pattern))
            | (models.DeliveryChallan.notes.ilike(search_pattern))
        )

    # Calculate pending and invoiced counts
    pending_count = (
        db.query(models.DeliveryChallan)
        .filter(models.DeliveryChallan.status == "PENDING")
        .count()
    )
    invoiced_count = (
        db.query(models.DeliveryChallan)
        .filter(models.DeliveryChallan.status == "INVOICED")
        .count()
    )

    total = query.count()
    challans = (
        query.order_by(models.DeliveryChallan.created_at.desc(), models.DeliveryChallan.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    results = []
    for c in challans:
        resolved_party_name = c.party_name or (c.party.name if c.party else None)
        resolved_invoice_num = c.invoice.invoice_number if c.invoice else None
        results.append(
            ChallanOut(
                id=c.id,
                challan_number=c.challan_number,
                party_id=c.party_id,
                party_name=resolved_party_name,
                image_url=c.image_url,
                notes=c.notes,
                status=c.status,
                invoice_id=c.invoice_id,
                invoice_number=resolved_invoice_num,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )

    return ChallanListResponse(
        items=results,
        total=total,
        pending_count=pending_count,
        invoiced_count=invoiced_count,
    )


@router.post("/", response_model=ChallanOut)
def create_challan(
    payload: ChallanCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    party_name = payload.party_name
    if payload.party_id and not party_name:
        party = db.query(models.Party).filter(models.Party.id == payload.party_id).first()
        if party:
            party_name = party.name

    # Auto-generate challan number if not provided
    challan_num = payload.challan_number
    if not challan_num:
        count = db.query(models.DeliveryChallan).count() + 1
        challan_num = f"DC-{count:04d}"

    challan = models.DeliveryChallan(
        challan_number=challan_num,
        party_id=payload.party_id,
        party_name=party_name,
        image_url=payload.image_url,
        notes=payload.notes,
        status="PENDING",
        created_by=current_user.id,
    )
    db.add(challan)
    db.commit()
    db.refresh(challan)

    return ChallanOut(
        id=challan.id,
        challan_number=challan.challan_number,
        party_id=challan.party_id,
        party_name=challan.party_name,
        image_url=challan.image_url,
        notes=challan.notes,
        status=challan.status,
        invoice_id=challan.invoice_id,
        invoice_number=None,
        created_at=challan.created_at,
        updated_at=challan.updated_at,
    )


@router.post("/{challan_id}/link", response_model=ChallanOut)
def link_challan_to_invoice(
    challan_id: int,
    invoice_id: int = Query(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    challan = (
        db.query(models.DeliveryChallan)
        .filter(models.DeliveryChallan.id == challan_id)
        .first()
    )
    if not challan:
        raise HTTPException(status_code=404, detail="Challan not found")

    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    challan.invoice_id = invoice.id
    challan.status = "INVOICED"
    if not invoice.delivery_challan_url:
        invoice.delivery_challan_url = challan.image_url

    db.commit()
    db.refresh(challan)

    return ChallanOut(
        id=challan.id,
        challan_number=challan.challan_number,
        party_id=challan.party_id,
        party_name=challan.party_name or (challan.party.name if challan.party else None),
        image_url=challan.image_url,
        notes=challan.notes,
        status=challan.status,
        invoice_id=challan.invoice_id,
        invoice_number=invoice.invoice_number,
        created_at=challan.created_at,
        updated_at=challan.updated_at,
    )


@router.delete("/{challan_id}")
def delete_challan(
    challan_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    challan = (
        db.query(models.DeliveryChallan)
        .filter(models.DeliveryChallan.id == challan_id)
        .first()
    )
    if not challan:
        raise HTTPException(status_code=404, detail="Challan not found")

    db.delete(challan)
    db.commit()
    return {"status": "success", "deleted_id": challan_id}


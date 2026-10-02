"""
Purchases Module — Vendors, Purchase Bills, Vendor Payments
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import models
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/purchases", tags=["purchases"])


# ──────────────────────────────────────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────────────────────────────────────

class VendorCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    gstin: Optional[str] = None
    tag: Optional[str] = None   # KARIGAR | Supplier | Other
    notes: Optional[str] = None


class VendorOut(BaseModel):
    id: int
    name: str
    phone: Optional[str]
    address: Optional[str]
    city: Optional[str]
    gstin: Optional[str]
    tag: Optional[str]
    notes: Optional[str]
    is_active: bool
    total_purchased: float = 0
    total_paid: float = 0
    balance_payable: float = 0

    model_config = {"from_attributes": True}


class PurchaseCreate(BaseModel):
    vendor_id: int
    bill_number: Optional[str] = None
    amount: Decimal
    purchase_date: str   # ISO date string
    description: Optional[str] = None


class PurchaseOut(BaseModel):
    id: int
    vendor_id: int
    vendor_name: Optional[str] = None
    bill_number: Optional[str]
    amount: Decimal
    balance_due: Decimal
    purchase_date: datetime
    description: Optional[str]
    is_paid: bool
    is_deleted: bool

    model_config = {"from_attributes": True}


class VendorPaymentCreate(BaseModel):
    vendor_id: int
    amount: Decimal
    payment_date: str
    mode: Optional[str] = "cash"
    note: Optional[str] = None
    purchase_id: Optional[int] = None   # optional link to specific bill


class VendorPaymentOut(BaseModel):
    id: int
    vendor_id: int
    vendor_name: Optional[str] = None
    amount: Decimal
    payment_date: datetime
    mode: Optional[str]
    note: Optional[str]
    purchase_id: Optional[int]

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────────────────────────
# Vendors
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/vendors", response_model=List[VendorOut])
def list_vendors(
    search: str = "",
    tag: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rows = db.execute(text("""
        WITH p_agg AS (
            SELECT vendor_id, COALESCE(SUM(amount),0) AS total_purchased
            FROM purchases WHERE is_deleted = false GROUP BY vendor_id
        ),
        pay_agg AS (
            SELECT vendor_id, COALESCE(SUM(amount),0) AS total_paid
            FROM vendor_payments WHERE is_deleted = false GROUP BY vendor_id
        )
        SELECT
            v.id, v.name, v.phone, v.address, v.city, v.gstin, v.tag, v.notes, v.is_active,
            COALESCE(p.total_purchased, 0) AS total_purchased,
            COALESCE(pay.total_paid, 0) AS total_paid,
            COALESCE(p.total_purchased, 0) - COALESCE(pay.total_paid, 0) AS balance_payable
        FROM vendors v
        LEFT JOIN p_agg p ON p.vendor_id = v.id
        LEFT JOIN pay_agg pay ON pay.vendor_id = v.id
        WHERE v.is_active = true
          AND (:search = '' OR v.name ILIKE :search_pat)
          AND (:tag IS NULL OR v.tag = :tag)
        ORDER BY v.name ASC
    """), {"search": search, "search_pat": f"%{search}%", "tag": tag}).fetchall()

    return [VendorOut(
        id=r.id, name=r.name, phone=r.phone, address=r.address, city=r.city,
        gstin=r.gstin, tag=r.tag, notes=r.notes, is_active=r.is_active,
        total_purchased=float(r.total_purchased),
        total_paid=float(r.total_paid),
        balance_payable=float(r.balance_payable),
    ) for r in rows]


@router.post("/vendors", response_model=VendorOut, status_code=status.HTTP_201_CREATED)
def create_vendor(
    data: VendorCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    vendor = models.Vendor(
        name=data.name, phone=data.phone, address=data.address,
        city=data.city, gstin=data.gstin, tag=data.tag, notes=data.notes,
        created_by=current_user.id,
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return VendorOut(id=vendor.id, name=vendor.name, phone=vendor.phone,
                     address=vendor.address, city=vendor.city, gstin=vendor.gstin,
                     tag=vendor.tag, notes=vendor.notes, is_active=vendor.is_active)


# ──────────────────────────────────────────────────────────────────────────────
# Purchases (Bills)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/bills", response_model=List[PurchaseOut])
def list_purchases(
    vendor_id: Optional[int] = None,
    unpaid_only: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rows = db.execute(text("""
        SELECT p.*, v.name AS vendor_name
        FROM purchases p
        JOIN vendors v ON v.id = p.vendor_id
        WHERE p.is_deleted = false
          AND (:vendor_id IS NULL OR p.vendor_id = :vendor_id)
          AND (:unpaid_only = false OR p.is_paid = false)
        ORDER BY p.purchase_date DESC
    """), {"vendor_id": vendor_id, "unpaid_only": unpaid_only}).fetchall()

    return [PurchaseOut(
        id=r.id, vendor_id=r.vendor_id, vendor_name=r.vendor_name,
        bill_number=r.bill_number, amount=r.amount, balance_due=r.balance_due,
        purchase_date=r.purchase_date, description=r.description,
        is_paid=r.is_paid, is_deleted=r.is_deleted,
    ) for r in rows]


@router.post("/bills", response_model=PurchaseOut, status_code=status.HTTP_201_CREATED)
def create_purchase(
    data: PurchaseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    vendor = db.query(models.Vendor).filter_by(id=data.vendor_id, is_active=True).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    purchase = models.Purchase(
        vendor_id=data.vendor_id,
        created_by=current_user.id,
        bill_number=data.bill_number,
        amount=data.amount,
        balance_due=data.amount,
        purchase_date=datetime.fromisoformat(data.purchase_date).replace(tzinfo=timezone.utc),
        description=data.description,
    )
    db.add(purchase)
    db.commit()
    db.refresh(purchase)
    return PurchaseOut(
        id=purchase.id, vendor_id=purchase.vendor_id, vendor_name=vendor.name,
        bill_number=purchase.bill_number, amount=purchase.amount, balance_due=purchase.balance_due,
        purchase_date=purchase.purchase_date, description=purchase.description,
        is_paid=purchase.is_paid, is_deleted=purchase.is_deleted,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Vendor Payments (Outgoing)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/payments", response_model=List[VendorPaymentOut])
def list_vendor_payments(
    vendor_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rows = db.execute(text("""
        SELECT vp.*, v.name AS vendor_name
        FROM vendor_payments vp
        JOIN vendors v ON v.id = vp.vendor_id
        WHERE vp.is_deleted = false
          AND (:vendor_id IS NULL OR vp.vendor_id = :vendor_id)
        ORDER BY vp.payment_date DESC
    """), {"vendor_id": vendor_id}).fetchall()

    return [VendorPaymentOut(
        id=r.id, vendor_id=r.vendor_id, vendor_name=r.vendor_name,
        amount=r.amount, payment_date=r.payment_date, mode=r.mode,
        note=r.note, purchase_id=r.purchase_id,
    ) for r in rows]


@router.post("/payments", response_model=VendorPaymentOut, status_code=status.HTTP_201_CREATED)
def create_vendor_payment(
    data: VendorPaymentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    vendor = db.query(models.Vendor).filter_by(id=data.vendor_id, is_active=True).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    payment = models.VendorPayment(
        vendor_id=data.vendor_id,
        created_by=current_user.id,
        amount=data.amount,
        payment_date=datetime.fromisoformat(data.payment_date).replace(tzinfo=timezone.utc),
        mode=data.mode,
        note=data.note,
        purchase_id=data.purchase_id,
    )
    db.add(payment)

    # Reduce balance_due on linked purchase if specified
    if data.purchase_id:
        purchase = db.query(models.Purchase).filter_by(id=data.purchase_id).first()
        if purchase:
            purchase.balance_due = max(Decimal("0"), purchase.balance_due - data.amount)
            if purchase.balance_due <= 0:
                purchase.is_paid = True

    db.commit()
    db.refresh(payment)
    return VendorPaymentOut(
        id=payment.id, vendor_id=payment.vendor_id, vendor_name=vendor.name,
        amount=payment.amount, payment_date=payment.payment_date,
        mode=payment.mode, note=payment.note, purchase_id=payment.purchase_id,
    )

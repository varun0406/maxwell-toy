from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Generic, TypeVar
from pydantic import BaseModel, EmailStr, Field, field_validator

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    skip: int
    limit: int
    summary_total: Optional[Decimal] = None
    meta: Optional[dict] = None


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: str = Field(min_length=4)

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username must be alphanumeric (underscores/hyphens allowed)")
        return v


class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str]
    is_active: bool
    is_superuser: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    username: str
    password: str


# ---------------------------------------------------------------------------
# Party
# ---------------------------------------------------------------------------

class PartyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=20)
    email: Optional[EmailStr] = None
    agent_name: Optional[str] = None
    billing_address_line1: Optional[str] = None
    billing_address_line2: Optional[str] = None
    billing_address_line3: Optional[str] = None
    billing_city: Optional[str] = None
    shipping_address_line1: Optional[str] = None
    shipping_address_line2: Optional[str] = None
    shipping_address_line3: Optional[str] = None
    shipping_city: Optional[str] = None
    area: Optional[str] = None
    gstin: Optional[str] = Field(default=None, max_length=20)
    notes: Optional[str] = None
    reminder_date: Optional[datetime] = None


class PartyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=20)
    email: Optional[EmailStr] = None
    agent_name: Optional[str] = None
    billing_address_line1: Optional[str] = None
    billing_address_line2: Optional[str] = None
    billing_address_line3: Optional[str] = None
    billing_city: Optional[str] = None
    shipping_address_line1: Optional[str] = None
    shipping_address_line2: Optional[str] = None
    shipping_address_line3: Optional[str] = None
    shipping_city: Optional[str] = None
    area: Optional[str] = None
    gstin: Optional[str] = Field(default=None, max_length=20)
    notes: Optional[str] = None
    reminder_date: Optional[datetime] = None
    is_active: Optional[bool] = None


class PartyOut(BaseModel):
    id: int
    name: str
    phone: Optional[str]
    email: Optional[str]
    agent_name: Optional[str]
    billing_address_line1: Optional[str]
    billing_address_line2: Optional[str]
    billing_address_line3: Optional[str]
    billing_city: Optional[str]
    shipping_address_line1: Optional[str]
    shipping_address_line2: Optional[str]
    shipping_address_line3: Optional[str]
    shipping_city: Optional[str]
    area: Optional[str]
    gstin: Optional[str]
    notes: Optional[str]
    reminder_date: Optional[datetime]
    busy_closing_balance: Optional[Decimal] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PartyWithBalance(PartyOut):
    total_invoiced: Decimal
    total_paid: Decimal
    total_journal: Decimal = Field(default=Decimal("0"))
    outstanding: Decimal
    bills_outstanding: Decimal = Field(default=Decimal("0"))
    unallocated_payments: Decimal = Field(default=Decimal("0"))
    overdue_days: int = Field(default=0)


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------

class ItemCreate(BaseModel):
    item_name: str = Field(min_length=1, max_length=200)
    default_rate: Optional[Decimal] = Field(default=Decimal("0"))

class ItemOut(BaseModel):
    id: int
    item_name: str
    default_rate: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------

class InvoiceItemCreate(BaseModel):
    item_name: str
    meter: Decimal = Field(gt=0)
    rate: Decimal = Field(gt=0)

class InvoiceItemOut(BaseModel):
    id: int
    invoice_id: int
    item_name: str
    meter: Decimal
    rate: Decimal
    total: Decimal
    
    model_config = {"from_attributes": True}

class InvoiceCreate(BaseModel):
    party_id: int
    invoice_number: Optional[str] = None  # auto-gen if not provided
    description: Optional[str] = None
    invoice_date: datetime
    due_date: Optional[datetime] = None
    billing_address: Optional[str] = None
    shipping_address: Optional[str] = None
    delivery_challan_url: Optional[str] = None
    items: List[InvoiceItemCreate]


class InvoiceUpdate(BaseModel):
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    invoice_date: Optional[datetime] = None
    billing_address: Optional[str] = None
    shipping_address: Optional[str] = None
    delivery_challan_url: Optional[str] = None
    items: Optional[List[InvoiceItemCreate]] = None


class AllocationOutForInvoice(BaseModel):
    id: int
    payment_id: Optional[int]
    journal_id: Optional[int]
    allocated_amount: Decimal
    created_at: datetime
    payment_mode: Optional[str]
    payment_date: Optional[datetime]
    note: Optional[str]

    model_config = {"from_attributes": True}


class InvoiceOut(BaseModel):
    id: int
    invoice_number: str
    party_id: int
    party_name: Optional[str] = None
    amount: Decimal
    balance_due: Decimal
    billing_address: Optional[str]
    shipping_address: Optional[str]
    description: Optional[str]
    invoice_date: datetime
    due_date: Optional[datetime]
    delivery_challan_url: Optional[str] = None
    is_paid: bool
    is_deleted: bool
    created_at: datetime
    items: List[InvoiceItemOut]
    allocations: List[AllocationOutForInvoice] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------

class AllocationCreate(BaseModel):
    invoice_id: int
    allocated_amount: Decimal = Field(gt=0)


class PaymentCreate(BaseModel):
    party_id: int
    amount: Decimal = Field(gt=0)
    payment_date: datetime
    note: Optional[str] = None
    mode: Optional[str] = Field(default="cash", max_length=30)
    allocations: Optional[List[AllocationCreate]] = None


class AllocationOut(BaseModel):
    invoice_id: int
    invoice_number: str
    allocated_amount: Decimal

    model_config = {"from_attributes": True}


class PaymentOut(BaseModel):
    id: int
    party_id: int
    party_name: Optional[str] = None
    amount: Decimal
    discount_amount: Decimal = Decimal("0")
    unallocated: Decimal
    payment_date: datetime
    note: Optional[str]
    mode: Optional[str]
    is_deleted: bool
    deleted_reason: Optional[str] = None  # F9
    created_at: datetime
    allocations: List[AllocationOut] = []

    model_config = {"from_attributes": True}


# F9 — Payment delete with reason
class PaymentDeleteRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=200)


# F13 — Payment edit (only non-allocation fields)
class PaymentUpdate(BaseModel):
    payment_date: Optional[datetime] = None
    mode: Optional[str] = Field(default=None, max_length=30)
    note: Optional[str] = None


# ---------------------------------------------------------------------------
# Journal Entries
# ---------------------------------------------------------------------------

class JournalEntryCreate(BaseModel):
    amount: Decimal
    entry_date: datetime
    account_id: Optional[int] = None
    description: Optional[str] = None

class JournalEntryOut(BaseModel):
    id: int
    party_id: int
    account_id: Optional[int] = None
    account_name: Optional[str] = None
    amount: Decimal
    entry_date: datetime
    description: Optional[str]
    is_deleted: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Account Masters
# ---------------------------------------------------------------------------

class AccountMasterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    group_name: Optional[str] = None

class AccountMasterOut(BaseModel):
    id: int
    name: str
    group_name: Optional[str]
    is_active: bool
    total_amount: Decimal = Decimal("0")
    entry_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Ledger (combined view per party)
# ---------------------------------------------------------------------------

class LedgerEntry(BaseModel):
    type: str          # "invoice" | "payment" | "journal"
    record_id: int     # ID of the corresponding record
    date: datetime
    reference: str     # invoice_number or "PMT-{id}"
    amount: Decimal
    balance_due: Optional[Decimal] = None   # for invoices
    running_balance: Decimal
    description: Optional[str] = None      # journal account name

# ---------------------------------------------------------------------------
# Agent / Area Analytics
# ---------------------------------------------------------------------------

class GroupedAnalytics(BaseModel):
    group_name: str
    total_invoiced: Decimal
    total_paid: Decimal
    total_journal: Decimal
    outstanding: Decimal
    party_count: int


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

class PartySummary(BaseModel):
    party_id: int
    party_name: str
    total_invoiced: Decimal
    total_paid: Decimal
    total_journal: Decimal = Field(default=Decimal("0"))
    outstanding: Decimal
    invoice_count: int
    payment_count: int

# ---------------------------------------------------------------------------
# Address Book
# ---------------------------------------------------------------------------

class AddressBookCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None

class AddressBookUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None

class AddressBookOut(AddressBookCreate):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}


# F12 — Collections breakdown by payment mode
class ModeBreakdown(BaseModel):
    mode: str
    total: Decimal
    count: int


class AgingBucket(BaseModel):
    party_id: int
    party_name: str
    current: Decimal       # 0-30 days
    days_31_60: Decimal
    days_61_90: Decimal
    over_90: Decimal
    total: Decimal


class OverduePartyOut(BaseModel):
    id: int
    name: str
    outstanding: Decimal
    overdue_days: int
    bills_count: int

class DashboardSummary(BaseModel):
    total_parties: int
    total_invoiced: Decimal
    total_collected: Decimal
    total_journal: Decimal = Field(default=Decimal("0"))
    total_outstanding: Decimal
    total_bills_outstanding: Decimal = Field(default=Decimal("0"))
    total_unallocated_payments: Decimal = Field(default=Decimal("0"))
    invoices_count: int
    overdue_count: int
    today_receipts: Decimal = Field(default=Decimal("0"))
    top_overdue_parties: List[OverduePartyOut] = []
    monthly_trend: List[CashFlowMonth] = []
    recent_payments: List[PaymentOut]

class PinReset(BaseModel):
    new_pin: str = Field(min_length=4)

class CashFlowMonth(BaseModel):
    month: str
    invoiced: Decimal
    collected: Decimal

class ExecutiveSummary(BaseModel):
    dso_days: Decimal
    unallocated_advance_pool: Decimal
    at_risk_ratio: Decimal
    journal_adjustment_ratio: Decimal
    top_10_concentration: Decimal

class FabricItemMetrics(BaseModel):
    item_name: str
    total_meterage: Decimal
    avg_realized_rate: Decimal
    avg_ticket_size: Decimal

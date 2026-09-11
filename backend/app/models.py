from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Text, Numeric, DateTime,
    ForeignKey, Boolean, UniqueConstraint
)
from sqlalchemy.orm import relationship
from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=True, index=True)
    hashed_password = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    parties = relationship("Party", back_populates="created_by_user")
    invoices = relationship("Invoice", back_populates="created_by_user")
    payments = relationship("Payment", back_populates="created_by_user")


class RefreshToken(Base):
    """Stored hashed refresh tokens for rotation & revocation."""
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(200), nullable=False, index=True)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="refresh_tokens")


# ---------------------------------------------------------------------------
# Parties
# ---------------------------------------------------------------------------

class Party(Base):
    __tablename__ = "parties"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    phone = Column(String(20), nullable=True)
    email = Column(String(120), nullable=True)
    agent_name = Column(String(120), nullable=True)
    billing_address_line1 = Column(String(255), nullable=True)
    billing_address_line2 = Column(String(255), nullable=True)
    billing_address_line3 = Column(String(255), nullable=True)
    billing_city = Column(String(120), nullable=True)
    shipping_address_line1 = Column(String(255), nullable=True)
    shipping_address_line2 = Column(String(255), nullable=True)
    shipping_address_line3 = Column(String(255), nullable=True)
    shipping_city = Column(String(120), nullable=True)
    gstin = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    is_active = Column(Boolean, default=True)

    created_by_user = relationship("User", back_populates="parties")
    invoices = relationship("Invoice", back_populates="party", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="party", cascade="all, delete-orphan")
    journal_entries = relationship("JournalEntry", back_populates="party", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Invoices (Sales)
# ---------------------------------------------------------------------------

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(50), nullable=False)
    party_id = Column(Integer, ForeignKey("parties.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Amounts stored as Numeric for precision
    amount = Column(Numeric(12, 2), nullable=False)          # Total invoice amount
    balance_due = Column(Numeric(12, 2), nullable=False)     # Remaining unpaid (decremented by FIFO)

    billing_address = Column(Text, nullable=True)
    shipping_address = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    invoice_date = Column(DateTime(timezone=True), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)
    is_paid = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    party = relationship("Party", back_populates="invoices")
    created_by_user = relationship("User", back_populates="invoices")
    allocations = relationship("PaymentAllocation", back_populates="invoice")

    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("invoice_number", "created_by", name="uq_invoice_no_per_user"),
    )

class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    item_name = Column(String(200), nullable=False)
    meter = Column(Numeric(12, 2), nullable=False)
    rate = Column(Numeric(12, 2), nullable=False)
    total = Column(Numeric(12, 2), nullable=False)

    invoice = relationship("Invoice", back_populates="items")


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    amount = Column(Numeric(12, 2), nullable=False)
    unallocated = Column(Numeric(12, 2), nullable=False, default=Decimal("0"))  # Overpayment / advance
    payment_date = Column(DateTime(timezone=True), nullable=False)
    note = Column(Text, nullable=True)
    mode = Column(String(30), nullable=True)  # cash / upi / bank
    is_deleted = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), default=utcnow)

    party = relationship("Party", back_populates="payments")
    created_by_user = relationship("User", back_populates="payments")
    allocations = relationship("PaymentAllocation", back_populates="payment", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Payment Allocations (Manual Linking)
# ---------------------------------------------------------------------------

class PaymentAllocation(Base):
    """Each row represents how much of a payment was manually applied to which invoice."""
    __tablename__ = "payment_allocations"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id", ondelete="CASCADE"), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    allocated_amount = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    payment = relationship("Payment", back_populates="allocations")
    invoice = relationship("Invoice", back_populates="allocations")


# ---------------------------------------------------------------------------
# Journal Entries (General Account Adjustments)
# ---------------------------------------------------------------------------

class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    amount = Column(Numeric(12, 2), nullable=False)  # Positive = Increase Due (Debit), Negative = Decrease Due (Credit)
    entry_date = Column(DateTime(timezone=True), nullable=False)
    description = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), default=utcnow)

    party = relationship("Party", back_populates="journal_entries")
    created_by_user = relationship("User")

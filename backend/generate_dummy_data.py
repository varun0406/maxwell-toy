"""
Maxwell Accounting — Realistic Dummy Data Generator
====================================================
Creates ~100 parties covering all real-world accounting edge cases:
  SCENARIO 1:  Fully paid parties (zero outstanding)
  SCENARIO 2:  Partially paid parties (balance due)
  SCENARIO 3:  Overdue — all 4 aging buckets (91+, 61-90, 31-60, <30 days)
  SCENARIO 4:  Advance / On-Account payments (unallocated credit)
  SCENARIO 5:  Multiple invoices per party (mixed paid/unpaid)
  SCENARIO 6:  Journal entry adjustments (discounts, returns, freight, interest)
  SCENARIO 7:  Invoice-only parties (no payment collected yet)
  SCENARIO 8:  High-value parties (for analytics top-line)
  SCENARIO 9:  Reversed/deleted entries (audit trail)
  SCENARIO 10: Agent-wise grouping (for agent/area reports)
  SCENARIO 11: Zero-transaction registered parties

All invoices include line items for correct PDF generation.

Run from backend directory:
    source venv/bin/activate
    python generate_dummy_data.py
"""

import sys
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import (
    User, Party, Invoice, InvoiceItem, ItemMaster,
    Payment, PaymentAllocation, JournalEntry
)
from app.auth import hash_password

# ── Helpers ──────────────────────────────────────────────────────────────────
now = datetime.now(timezone.utc)

def daysago(n: int) -> datetime:
    return now - timedelta(days=n)

def d(amount) -> Decimal:
    return Decimal(str(round(float(amount), 2)))

MODES = ["cash", "upi", "bank", "cheque"]
CITIES = ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Gandhinagar",
          "Bhavnagar", "Jamnagar", "Anand", "Mehsana", "Navsari",
          "Mumbai", "Delhi", "Bangalore", "Pune", "Hyderabad"]
AGENTS = ["Ramesh Shah", "Priya Patel", "Sunil Mehta", "Kavita Joshi", None, None]
AREAS  = ["Zone A", "Zone B", "Zone C", "North", "South", "East", "West", None]
ITEM_CATALOGUE = [
    ("Premium Fabric",  d(120)),
    ("Cotton Roll",     d(85)),
    ("Synthetic Blend", d(95)),
    ("Linen Grade A",   d(150)),
    ("Woolen Cloth",    d(200)),
    ("Denim Roll",      d(110)),
    ("Silk Fabric",     d(350)),
    ("Polyester Mix",   d(75)),
    ("Rayon Cloth",     d(90)),
    ("Chiffon",         d(180)),
]

_inv_counter = [1]

def next_inv() -> str:
    n = _inv_counter[0]
    _inv_counter[0] += 1
    return f"INV-{n:05d}"

def make_party(db, user, name, phone, city, agent=None, area=None):
    p = Party(name=name, phone=phone, billing_city=city,
              agent_name=agent, area=area, created_by=user.id, is_active=True)
    db.add(p)
    db.flush()
    return p

def make_invoice(db, party, user, inv_date, due_date, items, description=None):
    """items = list of (meters: float, rate: Decimal)"""
    total = sum(float(m) * float(r) for m, r in items)
    inv = Invoice(
        invoice_number=next_inv(),
        party_id=party.id,
        created_by=user.id,
        amount=d(total),
        balance_due=d(total),
        invoice_date=inv_date,
        due_date=due_date,
        description=description or "Supply of fabric rolls",
        billing_address=f"{party.billing_city}, Gujarat",
        shipping_address=f"{party.billing_city}, Gujarat",
        is_paid=False,
        is_deleted=False,
    )
    db.add(inv)
    db.flush()
    for (meters, rate) in items:
        item_name = next((n for n, r in ITEM_CATALOGUE if r == rate), "Fabric")
        db.add(InvoiceItem(
            invoice_id=inv.id,
            item_name=item_name,
            meter=d(meters),
            rate=d(rate),
            total=d(float(meters) * float(rate)),
        ))
    return inv

def make_payment(db, party, user, amount, pay_date, mode="cash",
                 note=None, alloc_list=None, unallocated_override=None):
    """alloc_list = list of (Invoice, amount_to_allocate)"""
    pmt = Payment(
        party_id=party.id,
        created_by=user.id,
        amount=d(amount),
        unallocated=d(unallocated_override if unallocated_override is not None else amount),
        payment_date=pay_date,
        mode=mode,
        note=note,
        is_deleted=False,
    )
    db.add(pmt)
    db.flush()
    if alloc_list:
        for inv, alloc_amt in alloc_list:
            db.add(PaymentAllocation(
                payment_id=pmt.id,
                invoice_id=inv.id,
                allocated_amount=d(alloc_amt),
            ))
            inv.balance_due = d(max(0, float(inv.balance_due) - float(alloc_amt)))
            if float(inv.balance_due) <= 0:
                inv.is_paid = True
            pmt.unallocated = d(max(0, float(pmt.unallocated) - float(alloc_amt)))
    return pmt

def make_journal(db, party, user, amount, entry_date, description):
    j = JournalEntry(party_id=party.id, created_by=user.id, amount=d(amount),
                     entry_date=entry_date, description=description, is_deleted=False)
    db.add(j)
    return j


# ── Main ─────────────────────────────────────────────────────────────────────
def run():
    db = SessionLocal()
    try:
        # ── Admin user ────────────────────────────────────────────────────────
        user = db.query(User).filter(User.username == "admin").first()
        if not user:
            user = User(username="admin", email="admin@maxwell.in",
                        hashed_password=hash_password("admin"), is_superuser=True)
            db.add(user)
            db.commit()
            db.refresh(user)
        print(f"✓ Admin user: {user.username} (id={user.id})")

        # ── Item master ───────────────────────────────────────────────────────
        for name, rate in ITEM_CATALOGUE:
            if not db.query(ItemMaster).filter(ItemMaster.item_name == name).first():
                db.add(ItemMaster(item_name=name, default_rate=rate))
        db.commit()
        print("✓ Item master seeded")

        # ════════════════════════════════════════════════════════════════════
        # SCENARIO 1: Fully Paid Parties (10) — zero outstanding
        # ════════════════════════════════════════════════════════════════════
        print("→ SC1: Fully Paid (10)")
        for i in range(1, 11):
            p = make_party(db, user, f"Fully Paid Co #{i}", f"98{i:08d}",
                           CITIES[i % len(CITIES)], AGENTS[i % len(AGENTS)], AREAS[i % len(AREAS)])
            inv1 = make_invoice(db, p, user, daysago(90), daysago(60),
                                [(100, d(120)), (50, d(85))], "Q1 Supply")
            inv2 = make_invoice(db, p, user, daysago(45), daysago(15),
                                [(80, d(95)), (30, d(150))], "Q2 Supply")
            total = float(inv1.amount) + float(inv2.amount)
            make_payment(db, p, user, total, daysago(10), mode=MODES[i % 4],
                         note="Full settlement",
                         alloc_list=[(inv1, float(inv1.amount)), (inv2, float(inv2.amount))],
                         unallocated_override=0)
        db.commit()

        # ════════════════════════════════════════════════════════════════════
        # SCENARIO 2: Partially Paid (15) — balance due
        # ════════════════════════════════════════════════════════════════════
        print("→ SC2: Partial Payers (15)")
        for i in range(1, 16):
            p = make_party(db, user, f"Partial Payer #{i}", f"97{i:08d}",
                           CITIES[(i + 3) % len(CITIES)], AGENTS[i % len(AGENTS)])
            inv_amt = 5000 + i * 1000
            inv = make_invoice(db, p, user, daysago(60 + i), daysago(30),
                               [(inv_amt // 100, d(100))], "Supply - partially settled")
            paid = inv_amt * 0.6
            make_payment(db, p, user, paid, daysago(20 + i), mode=MODES[i % 4],
                         note="Partial payment",
                         alloc_list=[(inv, paid)], unallocated_override=0)
        db.commit()

        # ════════════════════════════════════════════════════════════════════
        # SCENARIO 3: All 4 Overdue Buckets (8)
        # ════════════════════════════════════════════════════════════════════
        print("→ SC3: Overdue Buckets (8)")
        overdue_cases = [
            ("Overdue 91+ Days A",    110, 100, "Critical overdue - no payment"),
            ("Overdue 91+ Days B",     95,  85, "Long overdue balance"),
            ("Overdue 61-90 Days A",   75,  65, "2-month overdue"),
            ("Overdue 61-90 Days B",   70,  61, "Just past 2 months"),
            ("Overdue 31-60 Days A",   45,  32, "1-month overdue"),
            ("Overdue 31-60 Days B",   50,  35, "Recent overdue"),
            ("Overdue Under 30 Days A",25,  15, "Fresh overdue"),
            ("Overdue Under 30 Days B",20,  10, "Just overdue"),
        ]
        for i, (name, inv_days, due_days, desc) in enumerate(overdue_cases):
            p = make_party(db, user, name, f"96{i:08d}", CITIES[(i + 5) % len(CITIES)])
            make_invoice(db, p, user, daysago(inv_days), daysago(due_days),
                         [(200, d(120)), (100, d(95))], desc)
        db.commit()

        # ════════════════════════════════════════════════════════════════════
        # SCENARIO 4: Advance / On-Account Payments (8)
        # ════════════════════════════════════════════════════════════════════
        print("→ SC4: Advance/On-Account (8)")
        advance_cases = [
            ("Advance Payer - Raj Textiles",  50000, "Advance for bulk order",  "bank"),
            ("Advance Payer - Kumar Fabrics",  25000, "Security deposit",        "cheque"),
            ("Advance - Partial Alloc",        30000, None,                      "upi"),
            ("Advance - No Invoice Yet",       15000, "Invoice pending",         "cash"),
            ("Overpayment Scenario",           12000, "Customer overpaid by 2000","upi"),
            ("Cheque Advance Payer",            8000, "Cheque advance",          "cheque"),
            ("UPI Advance Payer",              20000, "UPI advance",             "upi"),
            ("Bank Advance Payer",             40000, "NEFT advance",            "bank"),
        ]
        for i, (name, amt, note, mode) in enumerate(advance_cases):
            p = make_party(db, user, name, f"95{i:08d}", CITIES[(i + 1) % len(CITIES)],
                           agent=AGENTS[i % len(AGENTS)])
            pmt = make_payment(db, p, user, amt, daysago(5 + i), mode=mode, note=note)
            if name == "Advance - Partial Alloc":
                inv = make_invoice(db, p, user, daysago(3), daysago(-15),
                                   [(100, d(150))], "Invoice against advance")
                alloc_amt = min(float(inv.amount), amt / 2)
                db.add(PaymentAllocation(payment_id=pmt.id, invoice_id=inv.id,
                                         allocated_amount=d(alloc_amt)))
                inv.balance_due = d(max(0, float(inv.balance_due) - alloc_amt))
                pmt.unallocated = d(max(0, float(pmt.unallocated) - alloc_amt))
            if name == "Overpayment Scenario":
                inv = make_invoice(db, p, user, daysago(10), daysago(0),
                                   [(100, d(100))], "Invoice fully paid with overpayment")
                db.add(PaymentAllocation(payment_id=pmt.id, invoice_id=inv.id,
                                         allocated_amount=d(10000)))
                inv.balance_due = d(0); inv.is_paid = True
                pmt.unallocated = d(2000)
        db.commit()

        # ════════════════════════════════════════════════════════════════════
        # SCENARIO 5: Multi-Invoice Parties (10)
        # ════════════════════════════════════════════════════════════════════
        print("→ SC5: Multi-Invoice (10)")
        for i in range(1, 11):
            p = make_party(db, user, f"Multi Invoice Party #{i}", f"94{i:08d}",
                           CITIES[(i + 7) % len(CITIES)], agent="Ramesh Shah", area="Zone A")
            invs = []
            for j in range(1, 5):
                inv = make_invoice(db, p, user, daysago(90 - j * 15), daysago(60 - j * 15),
                                   [(50 + j * 10, ITEM_CATALOGUE[j % len(ITEM_CATALOGUE)][1]),
                                    (20, d(85))], f"Q{j} Supply batch")
                invs.append(inv)
            # INV1 fully paid, INV2 fully paid, INV3 half paid, INV4 unpaid
            make_payment(db, p, user, float(invs[0].amount), daysago(55), mode="bank",
                         note="NEFT - INV1", alloc_list=[(invs[0], float(invs[0].amount))],
                         unallocated_override=0)
            make_payment(db, p, user, float(invs[1].amount), daysago(40), mode="upi",
                         note="UPI - INV2", alloc_list=[(invs[1], float(invs[1].amount))],
                         unallocated_override=0)
            make_payment(db, p, user, float(invs[2].amount) * 0.5, daysago(20), mode="cash",
                         note="Partial - INV3",
                         alloc_list=[(invs[2], float(invs[2].amount) * 0.5)],
                         unallocated_override=0)
        db.commit()

        # ════════════════════════════════════════════════════════════════════
        # SCENARIO 6: Journal Adjustments (8)
        # ════════════════════════════════════════════════════════════════════
        print("→ SC6: Journal Adjustments (8)")
        journal_cases = [
            ("Discount Party - Raj",     10000,  -500, "Discount on bulk order"),
            ("Rate Difference Party",    15000,   250, "Rate revision upward"),
            ("Return Credit Party",      20000, -2000, "Goods returned - credit note"),
            ("Freight Add-on Party",     12000,   800, "Freight charges added"),
            ("Quality Claim Party",      18000, -1500, "Quality deduction"),
            ("Interest Charge Party",    25000,  1200, "Late payment interest"),
            ("Rounding Adj Party",        5000,    -3, "Paise rounding adjustment"),
            ("Multi-Adjust Party",        8000,   600, "Multiple adjustments"),
        ]
        for i, (name, inv_amt, jnl_amt, jnl_desc) in enumerate(journal_cases):
            p = make_party(db, user, name, f"93{i:08d}", CITIES[(i + 2) % len(CITIES)])
            inv = make_invoice(db, p, user, daysago(30 + i), daysago(0),
                               [(inv_amt // 100, d(100))], "Supply")
            make_journal(db, p, user, jnl_amt, daysago(5 + i), jnl_desc)
            effective_due = inv_amt + jnl_amt
            if effective_due > 0:
                pmt_amt = effective_due * 0.8
                alloc = min(pmt_amt, float(inv.amount))
                unalloc = max(0, pmt_amt - float(inv.amount))
                make_payment(db, p, user, pmt_amt, daysago(2), mode=MODES[i % 4],
                             note="Payment after adjustment",
                             alloc_list=[(inv, alloc)], unallocated_override=unalloc)
        db.commit()

        # ════════════════════════════════════════════════════════════════════
        # SCENARIO 7: Invoice-Only Parties — no payment yet (8)
        # ════════════════════════════════════════════════════════════════════
        print("→ SC7: Invoice-Only (8)")
        invoice_only = [
            ("Fresh Invoice - Patel Bros",    daysago(5),   daysago(-25)),
            ("New Customer - Mehta Traders",  daysago(10),  daysago(-20)),
            ("Pending Bill - Sharma Fabrics", daysago(15),  daysago(-15)),
            ("Awaiting Payment - Joshi Co",   daysago(20),  daysago(-10)),
            ("Credit Hold - Gupta Mills",     daysago(45),  daysago(15)),
            ("Large Order - Singh Textiles",  daysago(60),  daysago(30)),
            ("Old Pending - Rao Industries",  daysago(90),  daysago(60)),
            ("Default Risk - Khan Trading",   daysago(120), daysago(90)),
        ]
        for i, (name, inv_date, due_date) in enumerate(invoice_only):
            p = make_party(db, user, name, f"92{i:08d}", CITIES[(i + 4) % len(CITIES)],
                           agent=AGENTS[(i + 3) % len(AGENTS)], area=AREAS[i % len(AREAS)])
            amt = 10000 + i * 5000
            make_invoice(db, p, user, inv_date, due_date,
                         [(amt // 120, d(120)), (50, d(85))], "Supply pending payment")
        db.commit()

        # ════════════════════════════════════════════════════════════════════
        # SCENARIO 8: High-Value Parties (5)
        # ════════════════════════════════════════════════════════════════════
        print("→ SC8: High-Value (5)")
        high_value = [
            ("Diamond Fabrics Pvt Ltd",    500000),
            ("National Textile Corp",      350000),
            ("Sunshine Garments Ltd",      275000),
            ("Royal Weaves Industries",    420000),
            ("Global Cloth Exports",       180000),
        ]
        for i, (name, inv_amt) in enumerate(high_value):
            p = make_party(db, user, name, f"91{i:08d}", CITIES[i % len(CITIES)],
                           agent="Sunil Mehta", area="Zone A")
            inv = make_invoice(db, p, user, daysago(45 + i * 5), daysago(15 + i),
                               [(inv_amt // 120, d(120)), (500, d(150))],
                               f"Bulk supply order #{10 + i}")
            paid = inv_amt * 0.7
            make_payment(db, p, user, paid, daysago(10 + i), mode="bank",
                         note="RTGS Payment", alloc_list=[(inv, paid)], unallocated_override=0)
        db.commit()

        # ════════════════════════════════════════════════════════════════════
        # SCENARIO 9: Reversed/Deleted Payments — audit trail (5)
        # ════════════════════════════════════════════════════════════════════
        print("→ SC9: Reversed/Deleted Entries (5)")
        for i in range(1, 6):
            p = make_party(db, user, f"Audit Trail Party #{i}", f"90{i:08d}",
                           CITIES[i % len(CITIES)])
            inv = make_invoice(db, p, user, daysago(30), daysago(0),
                               [(100, d(120)), (50, d(85))],
                               "Invoice with bounced cheque payment")
            pmt = make_payment(db, p, user, float(inv.amount), daysago(15), mode="cheque",
                               note="Cheque bounced - reversal",
                               alloc_list=[(inv, float(inv.amount))], unallocated_override=0)
            # Reverse: soft-delete payment, restore invoice balance
            pmt.is_deleted = True
            pmt.deleted_reason = "Cheque Bounce"
            pmt.deleted_at = daysago(10)
            inv.is_paid = False
            inv.balance_due = inv.amount
        db.commit()

        # ════════════════════════════════════════════════════════════════════
        # SCENARIO 10: Agent-wise Parties (12)
        # ════════════════════════════════════════════════════════════════════
        print("→ SC10: Agent-wise (12)")
        agent_data = [
            ("Ramesh Shah - Ahmedabad Client",  "Ramesh Shah", "Zone A", 30000, "Ahmedabad"),
            ("Ramesh Shah - Surat Client",      "Ramesh Shah", "Zone A", 22000, "Surat"),
            ("Ramesh Shah - Rajkot Client",     "Ramesh Shah", "Zone B", 18000, "Rajkot"),
            ("Priya Patel - Vadodara Client",   "Priya Patel", "Zone B", 45000, "Vadodara"),
            ("Priya Patel - Gandhinagar Client","Priya Patel", "Zone C", 33000, "Gandhinagar"),
            ("Priya Patel - Anand Client",      "Priya Patel", "Zone C", 27000, "Anand"),
            ("Sunil Mehta - Mumbai Client",     "Sunil Mehta", "North",  55000, "Mumbai"),
            ("Sunil Mehta - Pune Client",       "Sunil Mehta", "North",  42000, "Pune"),
            ("Sunil Mehta - Hyderabad Client",  "Sunil Mehta", "South",  38000, "Hyderabad"),
            ("Kavita Joshi - Bangalore Client", "Kavita Joshi","South",  25000, "Bangalore"),
            ("Kavita Joshi - Delhi Client",     "Kavita Joshi","East",   20000, "Delhi"),
            ("Kavita Joshi - Jamnagar Client",  "Kavita Joshi","West",   15000, "Jamnagar"),
        ]
        for i, (name, agent, area, inv_amt, city) in enumerate(agent_data):
            p = make_party(db, user, name, f"89{i:08d}", city, agent=agent, area=area)
            inv = make_invoice(db, p, user, daysago(20 + i), daysago(-10 + i),
                               [(inv_amt // 120, d(120)), (100, d(85))],
                               "Agent-routed supply")
            paid = inv_amt * 0.5
            make_payment(db, p, user, paid, daysago(5 + i), mode=MODES[i % 4],
                         note=f"Collected by {agent}",
                         alloc_list=[(inv, paid)], unallocated_override=0)
        db.commit()

        # ════════════════════════════════════════════════════════════════════
        # SCENARIO 11: Zero-Transaction Registered Parties (4)
        # ════════════════════════════════════════════════════════════════════
        print("→ SC11: Zero-Transaction (4)")
        for i in range(1, 5):
            make_party(db, user, f"Inactive Party #{i}", f"88{i:08d}",
                       CITIES[i % len(CITIES)])
        db.commit()

        # ── Final summary ─────────────────────────────────────────────────────
        total_parties  = db.query(Party).count()
        total_invoices = db.query(Invoice).count()
        total_payments = db.query(Payment).count()
        total_journals = db.query(JournalEntry).count()

        print("\n" + "=" * 55)
        print("✅  Realistic dummy data generated!")
        print(f"   Parties    : {total_parties}")
        print(f"   Invoices   : {total_invoices}")
        print(f"   Payments   : {total_payments}")
        print(f"   Journals   : {total_journals}")
        print("=" * 55)
        print("\nScenarios covered:")
        print("  ✓ Fully paid (zero balance)")
        print("  ✓ Partially paid (balance due)")
        print("  ✓ Overdue: 91+d / 61-90d / 31-60d / <30d buckets")
        print("  ✓ Advance / on-account (unallocated credit)")
        print("  ✓ Overpayment scenario")
        print("  ✓ Multi-invoice: paid / partial / unpaid mix")
        print("  ✓ Journal adjustments: discount, return, freight, interest")
        print("  ✓ Invoice-only (no payment)")
        print("  ✓ High-value parties for analytics top-line")
        print("  ✓ Reversed/deleted payments (audit trail)")
        print("  ✓ Agent & area grouping for filtered reports")
        print("  ✓ Zero-transaction registered parties")
        print("  ✓ Payment modes: Cash / UPI / Bank / Cheque")
        print("  ✓ Invoice line items for PDF generation")

    except Exception as e:
        import traceback
        print(f"\n❌ Error: {e}")
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    run()


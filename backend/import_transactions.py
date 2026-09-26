import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.exc import IntegrityError

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.models import Party, Invoice, InvoiceItem, Payment, JournalEntry, PaymentAllocation
from app.database import SessionLocal

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def parse_date(date_str):
    try:
        return datetime.strptime(date_str.strip(), '%d-%m-%Y').replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def to_decimal(s, default='0'):
    try:
        return Decimal(str(s).strip())
    except Exception:
        return Decimal(default)


def get_or_create_party(session, name):
    """Find existing party or create a minimal one so no invoice is lost."""
    if not name:
        return None
    name = name.strip()
    party = session.query(Party).filter(Party.name == name).first()
    if not party:
        party = Party(
            name=name,
            is_active=True,
            created_by=1
        )
        session.add(party)
        session.flush()
        print(f"  [AUTO-CREATED] Party: {name}")
    return party


def extract_address(node):
    """Extract address from BillingDetails if present."""
    billing_details = node.find('BillingDetails')
    if billing_details is None:
        return None
        
    parts = [
        billing_details.findtext('Address1', '').strip(),
        billing_details.findtext('Address2', '').strip(),
        billing_details.findtext('Address3', '').strip(),
        billing_details.findtext('Address4', '').strip(),
    ]
    parts = [p for p in parts if p]
    return ", ".join(parts) if parts else None


def get_party_address(party):
    """Combine party's billing address fields into a single string."""
    if not party:
        return None
    parts = [
        party.billing_address_line1,
        party.billing_address_line2,
        party.billing_address_line3,
        party.billing_city
    ]
    parts = [p.strip() for p in parts if p and p.strip()]
    return ", ".join(parts) if parts else None


def narration(vch_other_node):
    """Combine Narration1 + Narration2 if both present."""
    if vch_other_node is None:
        return None
    parts = []
    n1 = vch_other_node.findtext('Narration1', '').strip()
    n2 = vch_other_node.findtext('Narration2', '').strip()
    if n1:
        parts.append(n1)
    if n2:
        parts.append(n2)
    return " | ".join(parts) if parts else None


def build_sale_description(vch_no, sale_node):
    parts = []
    vch_other = sale_node.find('VchOtherInfoDetails')
    if vch_other is not None:
        pb_no = vch_other.findtext('PurchaseBillNo', '').strip()
        if pb_no and pb_no != vch_no:
            parts.append(f"Ref: {pb_no}")
        transport = vch_other.findtext('Transport', '').strip()
        if transport:
            parts.append(f"Transport: {transport}")
        gr_no = vch_other.findtext('GRNo', '').strip()
        if gr_no:
            parts.append(f"GR: {gr_no}")
        station = vch_other.findtext('Station', '').strip()
        if station:
            parts.append(f"Station: {station}")
        nar = narration(vch_other)
        if nar:
            parts.append(nar)
    broker = sale_node.findtext('BrokerName', '').strip()
    if broker and broker != 'DIRECT':
        parts.append(f"Broker: {broker}")
    return " | ".join(parts) if parts else f"Sale {vch_no}"


def allocate_bill_refs(session, payment, bill_refs_node):
    """
    Parse <BillRefs><BillDetails> and create PaymentAllocations.
    Also handles the flat <BillRefs><RefNo> pattern from PendingBillDetails.
    """
    if bill_refs_node is None:
        return

    # Pattern A: <BillDetails> children (AccEntries/AccDetail/BillRefs)
    bill_details = bill_refs_node.findall('BillDetails')
    # Pattern B: <BillRefs><RefNo> flat (PendingBillDetails)
    if not bill_details and bill_refs_node.findtext('RefNo'):
        bill_details = [bill_refs_node]

    for bd in bill_details:
        ref_no = bd.findtext('RefNo', '').strip()
        alloc_amt = abs(to_decimal(bd.findtext('Value1', '0')))
        if not ref_no or alloc_amt == 0:
            continue

        invoice = session.query(Invoice).filter(Invoice.invoice_number == ref_no).first()
        if not invoice:
            continue

        actual = min(alloc_amt, payment.unallocated, invoice.balance_due)
        if actual <= 0:
            continue

        session.add(PaymentAllocation(
            payment_id=payment.id,
            invoice_id=invoice.id,
            allocated_amount=actual
        ))
        payment.unallocated -= actual
        invoice.balance_due -= actual
        if invoice.balance_due <= Decimal('0'):
            invoice.is_paid = True


def import_invoice_items(session, invoice, parent_node):
    """Parse <ItemEntries> for a Sale or SaleReturn, return sum of items."""
    item_sum = Decimal('0')
    for item in parent_node.findall('.//ItemEntries/ItemDetail'):
        item_name = item.findtext('ItemName', 'Unknown').strip()
        qty = to_decimal(item.findtext('QtyMainUnit', '0'))
        price = to_decimal(item.findtext('Price', '0'))
        amt = to_decimal(item.findtext('Amt', '0'))
        alt_qty = item.findtext('QtyAltUnit', '').strip()   # Pcs count
        unit = item.findtext('UnitName', '').strip()

        # Enrich name with unit/pcs context
        if alt_qty and alt_qty != '0':
            full_name = f"{item_name} ({alt_qty} Pcs)"
        else:
            full_name = item_name

        session.add(InvoiceItem(
            invoice_id=invoice.id,
            item_name=full_name,
            meter=qty,
            rate=price,
            total=amt
        ))
        item_sum += amt
    return item_sum


def add_adjustment_item(session, invoice, diff, sale_node):
    """Add a BillSundries-named adjustment line item if total differs from sum of items."""
    bs_names = [
        bs.findtext('BSName', '').strip()
        for bs in sale_node.findall('.//BillSundries/BSDetail')
        if bs.findtext('BSName', '').strip()
    ]
    adj_name = " + ".join(bs_names) if bs_names else "Adjustments / Other Charges"
    session.add(InvoiceItem(
        invoice_id=invoice.id,
        item_name=adj_name,
        meter=Decimal('1'),
        rate=diff,
        total=diff
    ))


# ─────────────────────────────────────────────
# Main Import
# ─────────────────────────────────────────────

def import_transactions(file_path):
    print(f"\nParsing {file_path}...")
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except ET.ParseError:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = "<root>" + f.read() + "</root>"
        root = ET.fromstring(content)

    session = SessionLocal()
    stats = {
        'sales_found': 0, 'sales_imported': 0, 'sales_skipped': 0,
        'returns_found': 0, 'returns_imported': 0, 'returns_skipped': 0,
        'payments_found': 0, 'payments_imported': 0, 'payments_skipped': 0,
        'journals_found': 0, 'journals_imported': 0, 'journals_skipped': 0,
        'crnts_found': 0, 'crnts_imported': 0, 'crnts_skipped': 0,
        'adj_payments_imported': 0
    }

    # ── 1. SALES ───────────────────────────────────────
    print("\n[1/4] Importing Sales...")
    for sale in root.findall('.//Sales/Sale'):
        stats['sales_found'] += 1
        vch_no = sale.findtext('VchNo', '').strip()
        date_str = sale.findtext('Date', '')
        party_name = sale.findtext('MasterName1', '').strip()

        party = get_or_create_party(session, party_name)
        if not party:
            print(f"  SKIP (no party): {vch_no}")
            stats['sales_skipped'] += 1
            continue

        if session.query(Invoice).filter(Invoice.invoice_number == vch_no).first():
            stats['sales_skipped'] += 1
            continue  # already imported

        amount = to_decimal(sale.findtext('tmpTotalAmt', '0'))
        desc = build_sale_description(vch_no, sale)
        
        party_billing_addr = get_party_address(party)
        transaction_addr = extract_address(sale)

        invoice = Invoice(
            invoice_number=vch_no,
            party_id=party.id,
            created_by=1,
            amount=amount,
            balance_due=amount,
            invoice_date=parse_date(date_str),
            description=desc,
            billing_address=party_billing_addr,
            shipping_address=transaction_addr or party_billing_addr
        )
        session.add(invoice)
        session.flush()

        item_sum = import_invoice_items(session, invoice, sale)
        diff = amount - item_sum
        if abs(diff) > Decimal('0.01'):
            add_adjustment_item(session, invoice, diff, sale)

        stats['sales_imported'] += 1

    # ── 2. SALE RETURNS ────────────────────────────────
    print("\n[2/4] Importing Sale Returns (Credit Notes)...")
    for slrt in root.findall('.//SlRts/SaleReturn'):
        stats['returns_found'] += 1
        vch_no = slrt.findtext('VchNo', '').strip()
        inv_no = f"SR-{vch_no}"
        date_str = slrt.findtext('Date', '')
        party_name = slrt.findtext('MasterName1', '').strip()

        party = get_or_create_party(session, party_name)
        if not party:
            stats['returns_skipped'] += 1
            continue

        if session.query(Invoice).filter(Invoice.invoice_number == inv_no).first():
            stats['returns_skipped'] += 1
            continue

        # Amount is negative (reduces outstanding)
        raw_amt = to_decimal(slrt.findtext('tmpTotalAmt', '0'))
        amount = -abs(raw_amt)

        vch_other = slrt.find('VchOtherInfoDetails')
        desc_parts = ["Sale Return"]
        orig_ref = slrt.findtext('.//VchOtherInfoDetails/PurchaseBillNo', '').strip()
        if orig_ref:
            desc_parts.append(f"Against: {orig_ref}")
        nar = narration(vch_other)
        if nar:
            desc_parts.append(nar)
            
        party_billing_addr = get_party_address(party)
        transaction_addr = extract_address(slrt)

        invoice = Invoice(
            invoice_number=inv_no,
            party_id=party.id,
            created_by=1,
            amount=amount,
            balance_due=amount,
            invoice_date=parse_date(date_str),
            description=" | ".join(desc_parts),
            billing_address=party_billing_addr,
            shipping_address=transaction_addr or party_billing_addr
        )
        session.add(invoice)
        session.flush()

        # Import return items as negative amounts
        item_sum = Decimal('0')
        for item in slrt.findall('.//ItemEntries/ItemDetail'):
            item_name = item.findtext('ItemName', 'Unknown').strip()
            qty = to_decimal(item.findtext('QtyMainUnit', '0'))
            price = to_decimal(item.findtext('Price', '0'))
            amt = -abs(to_decimal(item.findtext('Amt', '0')))
            alt_qty = item.findtext('QtyAltUnit', '').strip()
            full_name = f"{item_name} ({alt_qty} Pcs)" if alt_qty and alt_qty != '0' else item_name

            session.add(InvoiceItem(
                invoice_id=invoice.id,
                item_name=full_name,
                meter=qty,
                rate=price,
                total=amt
            ))
            item_sum += amt

        diff = amount - item_sum
        if abs(diff) > Decimal('0.01'):
            add_adjustment_item(session, invoice, diff, slrt)

        stats['returns_imported'] += 1

    # ── 3. RECEIPTS ────────────────────────────────────
    print("\n[3/4] Importing Receipts...")
    for rcpt in root.findall('.//Rcpts/Receipt'):
        stats['payments_found'] += 1
        date_str = rcpt.findtext('Date', '')
        party = None
        amount = Decimal('0')
        note = ""
        mode = 'cash'
        debtor_acc = None

        vch_other = rcpt.find('VchOtherInfoDetails')
        nar = narration(vch_other)

        for acc in rcpt.findall('.//AccEntries/AccDetail'):
            grp = acc.findtext('tmpGroupName', '')
            if grp == 'Sundry Debtors':
                debtor_acc = acc
                party_name = acc.findtext('AccountName', '').strip()
                party = get_or_create_party(session, party_name)
                amount = abs(to_decimal(acc.findtext('AmtMainCur', '0')))
                sn = acc.findtext('ShortNar', '').strip()
                if sn:
                    note = sn
            elif grp in ['Bank Accounts', 'Cash-in-hand']:
                acc_name = acc.findtext('AccountName', '').lower()
                if any(kw in acc_name for kw in ['bank', 'hdfc', 'sbi', 'icici', 'axis']):
                    mode = 'bank'
                else:
                    mode = 'cash'

        # Narration overrides ShortNar if present
        if nar:
            note = nar

        if not party or amount == 0:
            stats['payments_skipped'] += 1
            continue

        p_date = parse_date(date_str)

        payment = Payment(
            party_id=party.id,
            created_by=1,
            amount=amount,
            unallocated=amount,
            payment_date=p_date,
            mode=mode,
            note=note
        )
        session.add(payment)
        session.flush()

        if debtor_acc is not None:
            allocate_bill_refs(session, payment, debtor_acc.find('BillRefs'))

        stats['payments_imported'] += 1

    # ── 4. JOURNALS ────────────────────────────────────
    print("\n[4/4] Importing Journal Entries...")
    for jrnl in root.findall('.//Jrnls/Journal'):
        stats['journals_found'] += 1
        date_str = jrnl.findtext('Date', '')
        p_date = parse_date(date_str)
        vch_other = jrnl.find('VchOtherInfoDetails')
        jrnl_nar = narration(vch_other)

        # Find contra (non-debtor) account name for description
        non_debtor_names = [
            acc.findtext('AccountName', '') 
            for acc in jrnl.findall('.//AccEntries/AccDetail')
            if acc.findtext('tmpGroupName', '') != 'Sundry Debtors'
        ]

        for acc in jrnl.findall('.//AccEntries/AccDetail'):
            if acc.findtext('tmpGroupName', '') != 'Sundry Debtors':
                continue

            party_name = acc.findtext('AccountName', '').strip()
            party = get_or_create_party(session, party_name)
            if not party:
                continue

            amt_str = acc.findtext('AmtMainCur', '0')
            amt_type = acc.findtext('AmountType', '1')
            raw = abs(to_decimal(amt_str))
            je_amt = -raw if amt_type == '2' else raw  # 2=Credit, reduces balance

            if je_amt == 0:
                continue

            desc = jrnl_nar or acc.findtext('ShortNar', '').strip()
            if not desc:
                desc = f"Journal: {', '.join(non_debtor_names)}" if non_debtor_names else "Journal Entry"

            bill_refs_node = acc.find('BillRefs')
            has_bill_refs = bill_refs_node is not None and (
                list(bill_refs_node.findall('BillDetails')) or
                bill_refs_node.findtext('RefNo')
            )

            # Credit journal with specific bill refs → treat as Adjustment Payment
            if je_amt < 0 and has_bill_refs:
                payment = Payment(
                    party_id=party.id,
                    created_by=1,
                    amount=abs(je_amt),
                    unallocated=abs(je_amt),
                    payment_date=p_date,
                    mode='adjustment',
                    note=desc
                )
                session.add(payment)
                session.flush()
                allocate_bill_refs(session, payment, bill_refs_node)
                stats['adj_payments_imported'] += 1
                stats['journals_imported'] += 1
            else:
                session.add(JournalEntry(
                    party_id=party.id,
                    created_by=1,
                    amount=je_amt,
                    entry_date=p_date,
                    description=desc
                ))
                stats['journals_imported'] += 1

    # ── 5. CREDIT NOTES (CrNts) ───────────────────────
    crnts = root.findall('.//CrNts/CrNt')
    if crnts:
        print(f"\n[5/5] Importing Credit Notes ({len(crnts)} records)...")
        for crnt in crnts:
            stats['crnts_found'] += 1
            vch_no = crnt.findtext('VchNo', '').strip()
            inv_no = f"CN-{vch_no}"
            date_str = crnt.findtext('Date', '')
            party_name = crnt.findtext('MasterName1', '').strip()

            party = get_or_create_party(session, party_name)
            if not party:
                stats['crnts_skipped'] += 1
                continue

            if session.query(Invoice).filter(Invoice.invoice_number == inv_no).first():
                stats['crnts_skipped'] += 1
                continue

            raw_amt = to_decimal(crnt.findtext('tmpTotalAmt', '0'))
            amount = -abs(raw_amt)  # Credit Note reduces outstanding

            vch_other = crnt.find('VchOtherInfoDetails')
            desc_parts = ["Credit Note"]
            orig_ref = crnt.findtext('.//VchOtherInfoDetails/PurchaseBillNo', '').strip()
            if orig_ref:
                desc_parts.append(f"Against: {orig_ref}")
            nar = narration(vch_other)
            if nar:
                desc_parts.append(nar)
                
            party_billing_addr = get_party_address(party)
            transaction_addr = extract_address(crnt)

            invoice = Invoice(
                invoice_number=inv_no,
                party_id=party.id,
                created_by=1,
                amount=amount,
                balance_due=amount,
                invoice_date=parse_date(date_str),
                description=" | ".join(desc_parts),
                billing_address=party_billing_addr,
                shipping_address=transaction_addr or party_billing_addr
            )
            session.add(invoice)
            session.flush()

            # Items
            item_sum = Decimal('0')
            for item in crnt.findall('.//ItemEntries/ItemDetail'):
                item_name = item.findtext('ItemName', 'Unknown').strip()
                qty = to_decimal(item.findtext('QtyMainUnit', '0'))
                price = to_decimal(item.findtext('Price', '0'))
                amt = -abs(to_decimal(item.findtext('Amt', '0')))
                session.add(InvoiceItem(
                    invoice_id=invoice.id,
                    item_name=item_name,
                    meter=qty,
                    rate=price,
                    total=amt
                ))
                item_sum += amt

            diff = amount - item_sum
            if abs(diff) > Decimal('0.01'):
                add_adjustment_item(session, invoice, diff, crnt)

            stats['crnts_imported'] += 1

    session.commit()
    session.close()

    print("\n" + "=" * 65)
    print(f"IMPORT COMPLETE: {file_path}")
    print("-" * 65)
    print(f"  Sales Invoices  | Found: {stats['sales_found']:<5} | Imported: {stats['sales_imported']:<5} | Skipped: {stats['sales_skipped']}")
    print(f"  Sale Returns    | Found: {stats['returns_found']:<5} | Imported: {stats['returns_imported']:<5} | Skipped: {stats['returns_skipped']}")
    print(f"  Credit Notes    | Found: {stats['crnts_found']:<5} | Imported: {stats['crnts_imported']:<5} | Skipped: {stats['crnts_skipped']}")
    print(f"  Receipts        | Found: {stats['payments_found']:<5} | Imported: {stats['payments_imported']:<5} | Skipped: {stats['payments_skipped']}")
    print(f"  Journal Entries | Found: {stats['journals_found']:<5} | Imported: {stats['journals_imported']:<5} | Skipped: {stats['journals_skipped']}")
    print("-" * 65)
    print(f"  (Note: Journals included {stats['adj_payments_imported']} Adjustment Payments)")
    print("=" * 65)


if __name__ == "__main__":
    import sys as _sys
    # Support passing multiple files as CLI args, e.g.:
    #   python import_transactions.py "../BUSY 25-26.DAT" ../TR.DAT
    files = _sys.argv[1:] if len(_sys.argv) > 1 else ["../TR.DAT"]
    for f in files:
        import_transactions(f)

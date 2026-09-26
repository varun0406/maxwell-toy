import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.models import Party, Invoice, InvoiceItem, Payment, JournalEntry, PaymentAllocation
from app.database import SessionLocal

def parse_date(date_str):
    """Parse DD-MM-YYYY string into a timezone-aware datetime."""
    try:
        dt = datetime.strptime(date_str, '%d-%m-%Y')
        return dt.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)

def get_party(session, name):
    if not name:
        return None
    return session.query(Party).filter(Party.name == name).first()

def get_amount(amt_str, amount_type):
    # amount_type '1' = Debit (increase debt -> positive)
    # amount_type '2' = Credit (decrease debt -> negative)
    try:
        val = abs(Decimal(amt_str))
        if amount_type == '2':
            return -val
        return val
    except:
        return Decimal('0')

def allocate_bill_refs(session, payment, bill_refs_node):
    """Parses <BillRefs> and creates PaymentAllocations for a given Payment."""
    if bill_refs_node is None:
        return
        
    for bd in bill_refs_node.findall('BillDetails'):
        ref_no = bd.findtext('RefNo')
        val_str = bd.findtext('Value1', '0')
        
        try:
            alloc_amt = abs(Decimal(val_str))
        except:
            continue
            
        if not ref_no or alloc_amt == 0:
            continue
            
        # Find invoice
        invoice = session.query(Invoice).filter(Invoice.invoice_number == ref_no).first()
        if not invoice:
            continue
            
        # Cap allocation to whatever is available
        actual_alloc = min(alloc_amt, payment.unallocated, invoice.balance_due)
        if actual_alloc <= 0:
            continue
            
        allocation = PaymentAllocation(
            payment_id=payment.id,
            invoice_id=invoice.id,
            allocated_amount=actual_alloc
        )
        session.add(allocation)
        
        # Update balances
        payment.unallocated -= actual_alloc
        invoice.balance_due -= actual_alloc
        if invoice.balance_due <= 0:
            invoice.is_paid = True


def import_transactions(file_path):
    print(f"Reading {file_path}...")
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except ET.ParseError:
        print("Parsing failed. Trying to wrap in a dummy root tag...")
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = "<root>" + f.read() + "</root>"
        root = ET.fromstring(content)

    session = SessionLocal()
    
    invoices_added = 0
    payments_added = 0
    journals_added = 0
    
    # 1. Import Sales
    print("Importing Sales...")
    for sale in root.findall('.//Sales/Sale'):
        vch_no = sale.findtext('VchNo', '')
        date_str = sale.findtext('Date', '')
        party_name = sale.findtext('MasterName1', '')
        
        party = get_party(session, party_name)
        if not party:
            continue
            
        existing_invoice = session.query(Invoice).filter(Invoice.invoice_number == vch_no).first()
        if existing_invoice:
            continue
            
        amount_str = sale.findtext('tmpTotalAmt', '0')
        try:
            amount = Decimal(amount_str)
        except:
            amount = Decimal('0')
            
        description = f"Sale Vch {vch_no}"
        
        invoice = Invoice(
            invoice_number=vch_no,
            party_id=party.id,
            created_by=1,
            amount=amount,
            balance_due=amount,
            invoice_date=parse_date(date_str),
            description=description
        )
        session.add(invoice)
        session.flush()
        invoices_added += 1
        
        item_sum = Decimal('0')
        for item_detail in sale.findall('.//ItemEntries/ItemDetail'):
            item_name = item_detail.findtext('ItemName', 'Unknown')
            qty_str = item_detail.findtext('QtyMainUnit', '0')
            price_str = item_detail.findtext('Price', '0')
            amt_str = item_detail.findtext('Amt', '0')
            
            try:
                qty = Decimal(qty_str)
                price = Decimal(price_str)
                item_amt = Decimal(amt_str)
            except:
                qty = Decimal('0')
                price = Decimal('0')
                item_amt = Decimal('0')
                
            inv_item = InvoiceItem(
                invoice_id=invoice.id,
                item_name=item_name,
                meter=qty,
                rate=price,
                total=item_amt
            )
            session.add(inv_item)
            item_sum += item_amt
            
        diff = amount - item_sum
        if abs(diff) > Decimal('0.01'):
            adj_item = InvoiceItem(
                invoice_id=invoice.id,
                item_name="Adjustments / Other Charges",
                meter=Decimal('1'),
                rate=diff,
                total=diff
            )
            session.add(adj_item)

    # 2. Import Sale Returns (SlRts)
    print("Importing Sale Returns...")
    for slrt in root.findall('.//SlRts/SaleReturn'):
        vch_no = slrt.findtext('VchNo', '')
        date_str = slrt.findtext('Date', '')
        party_name = slrt.findtext('MasterName1', '')
        
        party = get_party(session, party_name)
        if not party:
            continue
            
        existing_invoice = session.query(Invoice).filter(Invoice.invoice_number == f"SR-{vch_no}").first()
        if existing_invoice:
            continue
            
        amount_str = slrt.findtext('tmpTotalAmt', '0')
        try:
            amount = abs(Decimal(amount_str))
        except:
            amount = Decimal('0')
            
        invoice = Invoice(
            invoice_number=f"SR-{vch_no}",
            party_id=party.id,
            created_by=1,
            amount=-amount,
            balance_due=-amount,
            invoice_date=parse_date(date_str),
            description="Sale Return"
        )
        session.add(invoice)
        session.flush()
        invoices_added += 1

    # 3. Import Receipts (Payments)
    print("Importing Receipts...")
    for rcpt in root.findall('.//Rcpts/Receipt'):
        date_str = rcpt.findtext('Date', '')
        party = None
        amount = Decimal('0')
        note = "Imported from TR.DAT"
        mode = "cash"
        
        debtor_acc = None
        for acc in rcpt.findall('.//AccEntries/AccDetail'):
            grp = acc.findtext('tmpGroupName', '')
            if grp == 'Sundry Debtors':
                debtor_acc = acc
                party_name = acc.findtext('AccountName', '')
                party = get_party(session, party_name)
                
                amt_str = acc.findtext('AmtMainCur', '0')
                try:
                    amount = abs(Decimal(amt_str))
                except:
                    amount = Decimal('0')
                    
                short_nar = acc.findtext('ShortNar')
                if short_nar:
                    note = short_nar
            elif grp in ['Bank Accounts', 'Cash-in-hand']:
                acc_name = acc.findtext('AccountName', '').lower()
                if 'bank' in acc_name or 'hdfc' in acc_name or 'sbi' in acc_name:
                    mode = 'bank'
                elif 'cash' in acc_name:
                    mode = 'cash'
                
        if not party or amount == 0:
            continue
            
        payment = Payment(
            party_id=party.id,
            created_by=1,
            amount=amount,
            unallocated=amount,
            payment_date=parse_date(date_str),
            mode=mode,
            note=note
        )
        session.add(payment)
        session.flush() # flush to get payment.id
        
        # Parse Allocations
        if debtor_acc is not None:
            allocate_bill_refs(session, payment, debtor_acc.find('BillRefs'))
            
        payments_added += 1
        
    # 4. Import Journals
    print("Importing Journal Entries...")
    for jrnl in root.findall('.//Jrnls/Journal'):
        date_str = jrnl.findtext('Date', '')
        
        for acc in jrnl.findall('.//AccEntries/AccDetail'):
            grp = acc.findtext('tmpGroupName', '')
            if grp == 'Sundry Debtors':
                party_name = acc.findtext('AccountName', '')
                party = get_party(session, party_name)
                
                if not party:
                    continue
                    
                amt_str = acc.findtext('AmtMainCur', '0')
                amt_type = acc.findtext('AmountType', '1')
                je_amt = get_amount(amt_str, amt_type)
                
                if je_amt == 0:
                    continue
                    
                contra_acc = ""
                for c_acc in jrnl.findall('.//AccEntries/AccDetail'):
                    if c_acc.findtext('AccountName') != party_name:
                        contra_acc = c_acc.findtext('AccountName', '')
                        break
                        
                desc = acc.findtext('ShortNar', '')
                if not desc:
                    desc = f"Journal: {contra_acc}" if contra_acc else "Journal Entry"
                
                bill_refs = acc.find('BillRefs')
                # If this journal is a Credit (-) and has BillRefs, treat as Payment so we can allocate it to the Invoice!
                if je_amt < 0 and bill_refs is not None and list(bill_refs):
                    payment = Payment(
                        party_id=party.id,
                        created_by=1,
                        amount=abs(je_amt),
                        unallocated=abs(je_amt),
                        payment_date=parse_date(date_str),
                        mode='adjustment',
                        note=desc
                    )
                    session.add(payment)
                    session.flush()
                    allocate_bill_refs(session, payment, bill_refs)
                    payments_added += 1
                else:
                    je = JournalEntry(
                        party_id=party.id,
                        created_by=1,
                        amount=je_amt,
                        entry_date=parse_date(date_str),
                        description=desc
                    )
                    session.add(je)
                    journals_added += 1

    session.commit()
    session.close()
    print(f"Import complete! Added {invoices_added} invoices/returns, {payments_added} payments (incl. adjusting journals), and {journals_added} journal entries.")

if __name__ == "__main__":
    import_transactions("../TR.DAT")

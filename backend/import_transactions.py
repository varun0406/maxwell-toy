import os
import sys
import xml.etree.ElementTree as ET
from decimal import Decimal
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.models import Party, Invoice, InvoiceItem, Payment, PaymentAllocation, JournalEntry
from app.database import SessionLocal

def clean(value):
    return ' '.join((value or '').split()) or None

def parse_date(date_str):
    if not date_str:
        return datetime.utcnow()
    try:
        return datetime.strptime(date_str, "%d-%m-%Y")
    except:
        return datetime.utcnow()

def import_transactions(file_path, session):
    print(f"\n--- Reading {file_path} ---")
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return

    print("1. Building Mappings...")
    account_map = {}
    for acc in root.findall('.//Account'):
        code = acc.findtext('tmpCode')
        name = clean(acc.findtext('Name'))
        if code and name:
            account_map[code] = name

    item_map = {}
    for it in root.findall('.//Item'):
        code = it.findtext('tmpCode')
        name = clean(it.findtext('Name'))
        if code and name:
            item_map[code] = name

    db_parties = {p.name: p.id for p in session.query(Party).all()}

    def get_or_create_party(name):
        if not name:
            return None
        if name in db_parties:
            return db_parties[name]
        # Create missing party on the fly
        new_party = Party(name=name, is_active=True, created_by=1)
        session.add(new_party)
        session.flush()
        db_parties[name] = new_party.id
        return new_party.id

    # ---------------------------------------------------------
    # Import Sales (Invoices)
    # ---------------------------------------------------------
    print("2. Importing Sales...")
    sales_added = 0
    
    for sale in root.findall('.//Sale'):
        vch_no = clean(sale.findtext('VchNo'))
        date_str = clean(sale.findtext('Date'))
        party_tmpcode = sale.findtext('tmpMasterCode1')
        total_amt = Decimal(sale.findtext('tmpTotalAmt') or '0')
        
        party_name = account_map.get(party_tmpcode)
        if not party_name:
            party_name = clean(sale.findtext('MasterName1'))
            
        party_id = get_or_create_party(party_name)
        if not party_id:
            continue
            
        inv_date = parse_date(date_str)
        
        # Check if already exists in DB (just in case)
        existing = session.query(Invoice).filter_by(invoice_number=vch_no, party_id=party_id).first()
        if existing:
            continue
        
        invoice = Invoice(
            invoice_number=vch_no,
            party_id=party_id,
            created_by=1,
            amount=total_amt,
            balance_due=total_amt, # Will be decremented by manual allocations
            invoice_date=inv_date,
            is_paid=False,
            is_deleted=False
        )
        session.add(invoice)
        session.flush()
        
        # Line Items
        item_entries = sale.find('ItemEntries')
        if item_entries is not None:
            for item_det in item_entries.findall('ItemDetail'):
                i_code = item_det.findtext('tmpItemCode')
                i_name = item_map.get(i_code)
                if not i_name:
                    i_name = clean(item_det.findtext('ItemName')) or "Unknown Item"
                
                qty = Decimal(item_det.findtext('Qty') or '1')
                price = Decimal(item_det.findtext('Price') or '0')
                amt = Decimal(item_det.findtext('Amt') or item_det.findtext('Amount') or '0')
                
                inv_item = InvoiceItem(
                    invoice_id=invoice.id,
                    item_name=i_name,
                    meter=qty,
                    rate=price,
                    total=amt
                )
                session.add(inv_item)
                
        sales_added += 1

    session.commit()
    print(f"Sales: Added {sales_added}")

    # ---------------------------------------------------------
    # Import Receipts (Payments) with Bill-by-Bill Allocation
    # ---------------------------------------------------------
    print("3. Importing Receipts...")
    rcpts_added = 0
    
    for rcpt in root.findall('.//Receipt'):
        date_str = clean(rcpt.findtext('Date'))
        pay_date = parse_date(date_str)
        
        acc_entries = rcpt.find('AccEntries')
        if acc_entries is None:
            continue
            
        # Find the customer ledger entry (usually credit, AmountType 2)
        for acc_det in acc_entries.findall('AccDetail'):
            amt_type = acc_det.findtext('AmountType')
            # 2 = Credit (Customer paying us)
            # Or if group is Sundry Debtors
            if amt_type != '2':
                continue
                
            acc_code = acc_det.findtext('tmpAccCode')
            party_name = account_map.get(acc_code)
            if not party_name:
                party_name = clean(acc_det.findtext('AccountName'))
                
            party_id = get_or_create_party(party_name)
            if not party_id:
                continue
                
            pay_amount = Decimal(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount') or '0')
            if pay_amount <= 0:
                continue
                
            payment = Payment(
                party_id=party_id,
                created_by=1,
                amount=pay_amount,
                unallocated=pay_amount, # Default to fully unallocated
                payment_date=pay_date,
                mode='cash'
            )
            session.add(payment)
            session.flush()
            
            # Exact Bill-by-Bill manual allocation
            bill_refs = acc_det.find('BillRefs')
            if bill_refs is not None:
                for bill_det in bill_refs.findall('BillDetails'):
                    ref_no = clean(bill_det.findtext('RefNo'))
                    val_str = bill_det.findtext('Value1')
                    if not ref_no or not val_str:
                        continue
                        
                    alloc_amt = Decimal(val_str)
                    if alloc_amt <= 0:
                        continue
                        
                    # Find exact invoice
                    inv = session.query(Invoice).filter_by(invoice_number=ref_no, party_id=party_id).first()
                    if inv:
                        alloc = PaymentAllocation(
                            payment_id=payment.id,
                            invoice_id=inv.id,
                            allocated_amount=alloc_amt
                        )
                        session.add(alloc)
                        
                        # Decrease invoice balance_due
                        inv.balance_due -= alloc_amt
                        if inv.balance_due <= 0:
                            inv.balance_due = 0
                            inv.is_paid = True
                            
                        # Decrease payment unallocated
                        payment.unallocated -= alloc_amt

            rcpts_added += 1

    print(f"Receipts: Added {rcpts_added}")
    
    # ---------------------------------------------------------
    # Import Journals (Manual Adjustments)
    # ---------------------------------------------------------
    print("4. Importing Journals...")
    jrnl_added = 0
    for jrnl in root.findall('.//Journal'):
        date_str = clean(jrnl.findtext('Date'))
        jrnl_date = parse_date(date_str)
        
        acc_entries = jrnl.find('AccEntries')
        if acc_entries is None:
            continue
            
        for acc_det in acc_entries.findall('AccDetail'):
            acc_code = acc_det.findtext('tmpAccCode')
            party_name = account_map.get(acc_code)
            if not party_name:
                party_name = clean(acc_det.findtext('AccountName'))
                
            # Try to map only if it's a Sundry Debtor / Party in DB
            if not party_name or party_name not in db_parties:
                continue
                
            party_id = db_parties[party_name]
            amt_type = acc_det.findtext('AmountType')
            amt = Decimal(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount') or '0')
            
            if amt <= 0:
                continue
                
            # AmountType 1 = Debit (Increase Due), AmountType 2 = Credit (Decrease Due)
            if amt_type == '2':
                amt = -amt
                
            j_entry = session.query(JournalEntry).filter_by(
                party_id=party_id, amount=amt, entry_date=jrnl_date
            ).first()
            if not j_entry:
                session.add(JournalEntry(
                    party_id=party_id,
                    created_by=1,
                    amount=amt,
                    entry_date=jrnl_date,
                    description="Imported Journal Entry"
                ))
                jrnl_added += 1

    print(f"Journals: Added {jrnl_added}")

    # ---------------------------------------------------------
    # Import Sale Returns
    # ---------------------------------------------------------
    print("5. Importing Sale Returns...")
    sr_added = 0
    for sr in root.findall('.//SaleReturn'):
        vch_no = clean(sr.findtext('VchNo'))
        date_str = clean(sr.findtext('Date'))
        party_tmpcode = sr.findtext('tmpMasterCode1')
        total_amt = Decimal(sr.findtext('tmpTotalAmt') or '0')
        
        party_name = account_map.get(party_tmpcode)
        if not party_name:
            party_name = clean(sr.findtext('MasterName1'))
            
        party_id = get_or_create_party(party_name)
        if not party_id or total_amt <= 0:
            continue
            
        sr_date = parse_date(date_str)
        
        # Add as negative Journal Entry
        j_entry = session.query(JournalEntry).filter_by(
            party_id=party_id, amount=-total_amt, entry_date=sr_date
        ).first()
        if not j_entry:
            session.add(JournalEntry(
                party_id=party_id,
                created_by=1,
                amount=-total_amt,
                entry_date=sr_date,
                description=f"Sale Return: {vch_no}"
            ))
            sr_added += 1
            
    print(f"Sale Returns: Added {sr_added}")

    session.commit()

if __name__ == "__main__":
    files = sys.argv[1:]
    if not files:
        print("Please provide file paths")
        sys.exit(1)
        
    session = SessionLocal()
    for f in files:
        import_transactions(f, session)
    session.close()

import os
import sys
import xml.etree.ElementTree as ET
from decimal import Decimal
from datetime import datetime
from itertools import chain

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.models import Party, Invoice, InvoiceItem, Payment, PaymentAllocation, JournalEntry, AccountMaster
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

# ============================================================================
# MASTER ACCOUNT CACHE
# ============================================================================
account_master_cache = {}

def get_or_create_account_master(session, name, group_name=None):
    """Get or create an AccountMaster (Cash Discount, Rate Difference, etc.)"""
    if not name:
        return None
    name = clean(name)
    if name in account_master_cache:
        return account_master_cache[name]
    existing = session.query(AccountMaster).filter(AccountMaster.name == name).first()
    if existing:
        account_master_cache[name] = existing.id
        return existing.id
    acct = AccountMaster(name=name, group_name=group_name)
    session.add(acct)
    session.flush()
    account_master_cache[name] = acct.id
    return acct.id


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
    account_group_map = {}  # code -> group name
    for acc in root.findall('.//Account'):
        code = acc.findtext('tmpCode')
        name = clean(acc.findtext('Name'))
        grp = clean(acc.findtext('tmpGroupName'))
        if code and name:
            account_map[code] = name
            if grp:
                account_group_map[code] = grp

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
        
        existing = session.query(Invoice).filter_by(invoice_number=vch_no, party_id=party_id).first()
        if existing:
            continue
        
        invoice = Invoice(
            invoice_number=vch_no,
            party_id=party_id,
            created_by=1,
            amount=total_amt,
            balance_due=total_amt,
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
    # Now also captures ALL contra accounts (Cash Discount, 
    # Rate Difference, Dalali, Diwali Bonus, etc.) as 
    # Journal Entries linked to the master account
    # ---------------------------------------------------------
    print("3. Importing Receipts...")
    rcpts_added = 0
    contra_journals_added = 0
    
    for rcpt in root.findall('.//Receipt'):
        date_str = clean(rcpt.findtext('Date'))
        pay_date = parse_date(date_str)
        
        acc_entries = rcpt.find('AccEntries')
        if acc_entries is None:
            continue
        
        # Collect all entries categorized
        debtor_entries = []
        contra_entries = []
        
        for acc_det in acc_entries.findall('AccDetail'):
            grp = acc_det.findtext('tmpGroupName') or ''
            amt_type = acc_det.findtext('AmountType')
            amt = Decimal(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount') or '0')
            acc_code = acc_det.findtext('tmpAccCode')
            acc_name = account_map.get(acc_code) or clean(acc_det.findtext('AccountName'))
            
            if grp == 'Sundry Debtors':
                debtor_entries.append({
                    'acc_det': acc_det,
                    'name': acc_name,
                    'amt_type': amt_type,
                    'amt': amt,
                    'code': acc_code,
                })
            elif grp not in ('Cash-in-hand', 'Bank Accounts', 'Bank (OD/CC)'):
                # This is a contra account (expense/income like Cash Discount, Dalali, etc.)
                contra_entries.append({
                    'name': acc_name,
                    'group': grp,
                    'amt_type': amt_type,
                    'amt': amt,
                    'code': acc_code,
                })
        
        if not debtor_entries:
            continue
            
        # Process each debtor entry in this receipt
        for deb in debtor_entries:
            acc_det = deb['acc_det']
            party_name = deb['name']
            pay_amount = deb['amt']
            
            if pay_amount <= 0:
                continue
                
            party_id = get_or_create_party(party_name)
            if not party_id:
                continue

            # Calculate total discount (all contra entries in this receipt)
            discount = Decimal('0')
            for c in contra_entries:
                discount += c['amt']
            
            payment = Payment(
                party_id=party_id,
                created_by=1,
                amount=pay_amount,
                discount_amount=abs(discount) if len(debtor_entries) == 1 else Decimal('0'),
                unallocated=pay_amount,
                payment_date=pay_date,
                mode='cash'
            )
            session.add(payment)
            session.flush()
            
            # Bill-by-Bill allocation from BillRefs
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
                        
                    inv = session.query(Invoice).filter_by(invoice_number=ref_no, party_id=party_id).first()
                    if inv:
                        alloc = PaymentAllocation(
                            payment_id=payment.id,
                            invoice_id=inv.id,
                            allocated_amount=alloc_amt
                        )
                        session.add(alloc)
                        
                        inv.balance_due -= alloc_amt
                        if inv.balance_due <= 0:
                            inv.balance_due = 0
                            inv.is_paid = True
                            
                        payment.unallocated -= alloc_amt

            rcpts_added += 1
        
        # Create Journal Entries for each contra account (Cash Discount, Dalali, etc.)
        # These are TRACKING entries only — the customer's balance is already fully 
        # handled by the Receipt above. The contra journal records which master account 
        # absorbed the difference, without affecting the customer's outstanding.
        if contra_entries and len(debtor_entries) == 1:
            party_id = get_or_create_party(debtor_entries[0]['name'])
            if party_id:
                for c in contra_entries:
                    acct_id = get_or_create_account_master(session, c['name'], c['group'])
                    
                    # Amount = 0 (doesn't affect customer outstanding)
                    # The actual contra amount is stored for reporting via account_master aggregation
                    contra_amt = abs(c['amt'])
                    
                    j_entry = JournalEntry(
                        party_id=party_id,
                        account_id=acct_id,
                        created_by=1,
                        amount=Decimal('0'),  # Zero impact on customer balance
                        contra_amount=Decimal(str(contra_amt)),  # For master account reporting
                        entry_date=pay_date,
                        description=f"Receipt Adj: {c['name']}"
                    )
                    session.add(j_entry)
                    contra_journals_added += 1

    print(f"Receipts: Added {rcpts_added}")
    print(f"  Contra Journals (Discount/Dalali/etc.): Added {contra_journals_added}")
    
    # ---------------------------------------------------------
    # Import Journals, CrNotes, DbNotes
    # ---------------------------------------------------------
    print("4. Importing Journals & Notes...")
    jrnl_added = 0
    for jrnl in chain(root.findall('.//Journal'), root.findall('.//CrNote'), root.findall('.//DbNote')):
        date_str = clean(jrnl.findtext('Date'))
        jrnl_date = parse_date(date_str)
        
        acc_entries = jrnl.find('AccEntries')
        if acc_entries is None:
            continue
        
        # Identify debtor and contra entries
        debtor_entries = []
        contra_entries = []
        
        for acc_det in acc_entries.findall('AccDetail'):
            grp = acc_det.findtext('tmpGroupName') or ''
            acc_code = acc_det.findtext('tmpAccCode')
            acc_name = account_map.get(acc_code) or clean(acc_det.findtext('AccountName'))
            amt_type = acc_det.findtext('AmountType')
            amt = Decimal(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount') or '0')
            
            if grp == 'Sundry Debtors':
                debtor_entries.append({
                    'acc_det': acc_det,
                    'name': acc_name,
                    'amt_type': amt_type,
                    'amt': amt,
                    'code': acc_code,
                })
            else:
                contra_entries.append({
                    'name': acc_name,
                    'group': grp,
                    'amt_type': amt_type,
                    'amt': amt,
                    'code': acc_code,
                })
        
        if not debtor_entries:
            continue
            
        for deb in debtor_entries:
            acc_det = deb['acc_det']
            party_name = deb['name']
            
            if not party_name or party_name not in db_parties:
                continue
                
            party_id = db_parties[party_name]
            amt_type = deb['amt_type']
            amt = deb['amt']
            
            if amt <= 0:
                continue
                
            # AmountType 1 = Debit (Increase Due), AmountType 2 = Credit (Decrease Due)
            if amt_type == '2':
                amt = -amt
            
            # Determine contra account
            acct_id = None
            contra_desc = "Imported Journal Entry"
            if contra_entries:
                # Use the first contra account as the master account for this journal
                c = contra_entries[0]
                acct_id = get_or_create_account_master(session, c['name'], c['group'])
                contra_desc = f"Journal: {c['name']}"
                
            j_entry = session.query(JournalEntry).filter_by(
                party_id=party_id, amount=amt, entry_date=jrnl_date
            ).first()
            if not j_entry:
                j_entry = JournalEntry(
                    party_id=party_id,
                    account_id=acct_id,
                    created_by=1,
                    amount=amt,
                    entry_date=jrnl_date,
                    description=contra_desc
                )
                session.add(j_entry)
                session.flush()
                jrnl_added += 1

                # Parse BillRefs for allocating against Invoices
                bill_refs = acc_det.find('BillRefs')
                if bill_refs is not None:
                    for bill_det in bill_refs.findall('BillDetails'):
                        method = bill_det.findtext('Method')
                        if method == '2':
                            ref_no = clean(bill_det.findtext('RefNo'))
                            val = Decimal(bill_det.findtext('Value1') or '0')
                            val = abs(val)
                            
                            invoice = session.query(Invoice).filter_by(party_id=party_id, invoice_number=ref_no).first()
                            if invoice:
                                alloc = PaymentAllocation(
                                    journal_id=j_entry.id,
                                    invoice_id=invoice.id,
                                    allocated_amount=val
                                )
                                session.add(alloc)
                                
                                if amt_type == '2':
                                    invoice.balance_due -= val
                                else:
                                    invoice.balance_due += val
                                    
                                if invoice.balance_due <= 0:
                                    invoice.is_paid = True
                                else:
                                    invoice.is_paid = False

    print(f"Journals: Added {jrnl_added}")

    # ---------------------------------------------------------
    # Import Payments (Outgoing cash / Debits) as Journals
    # ---------------------------------------------------------
    print("4b. Importing Payments (Outgoing)...")
    pay_added = 0
    for out_pay in root.findall('.//Payment'):
        date_str = clean(out_pay.findtext('Date'))
        pay_date = parse_date(date_str)
        
        acc_entries = out_pay.find('AccEntries')
        if acc_entries is None:
            continue
            
        for acc_det in acc_entries.findall('AccDetail'):
            grp = acc_det.findtext('tmpGroupName') or ''
            if grp != 'Sundry Debtors':
                continue
                
            acc_code = acc_det.findtext('tmpAccCode')
            party_name = account_map.get(acc_code)
            if not party_name:
                party_name = clean(acc_det.findtext('AccountName'))
                
            if not party_name or party_name not in db_parties:
                continue
                
            party_id = db_parties[party_name]
            amt_type = acc_det.findtext('AmountType')
            amt = Decimal(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount') or '0')
            
            if amt <= 0:
                continue
                
            if amt_type == '2':
                amt = -amt
                
            j_entry = session.query(JournalEntry).filter_by(
                party_id=party_id, amount=amt, entry_date=pay_date
            ).first()
            if not j_entry:
                session.add(JournalEntry(
                    party_id=party_id,
                    created_by=1,
                    amount=amt,
                    entry_date=pay_date,
                    description="Imported Outgoing Payment"
                ))
                pay_added += 1

    print(f"Payments (Outgoing): Added {pay_added}")

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
        
        j_entry = session.query(JournalEntry).filter_by(
            party_id=party_id, amount=-total_amt, entry_date=sr_date
        ).first()
        if not j_entry:
            j_entry = JournalEntry(
                party_id=party_id,
                created_by=1,
                amount=-total_amt,
                entry_date=sr_date,
                description=f"Sale Return: {vch_no}"
            )
            session.add(j_entry)
            session.flush()
            sr_added += 1
            
            # Parse BillRefs for allocating against Invoices
            for bill_det in sr.findall('.//BillDetails'):
                method = bill_det.findtext('Method')
                if method == '2':
                    ref_no = clean(bill_det.findtext('RefNo'))
                    val = Decimal(bill_det.findtext('Value1') or '0')
                    val = abs(val)
                    
                    invoice = session.query(Invoice).filter_by(party_id=party_id, invoice_number=ref_no).first()
                    if invoice:
                        alloc = PaymentAllocation(
                            journal_id=j_entry.id,
                            invoice_id=invoice.id,
                            allocated_amount=val
                        )
                        session.add(alloc)
                        invoice.balance_due -= val
                        if invoice.balance_due <= 0:
                            invoice.is_paid = True
                        else:
                            invoice.is_paid = False
            
    print(f"Sale Returns: Added {sr_added}")

    session.commit()

def calculate_busy_balances(files, session):
    from app.models import Party
    print("\n--- Calculating Final BUSY Balances ---")
    
    party_balances = {}
    for f in files:
        tree = ET.parse(f)
        root = tree.getroot()
        for acc_det in root.findall('.//AccDetail'):
            name = ' '.join((acc_det.findtext('AccountName') or '').split())
            amt_type = acc_det.findtext('AmountType')
            amt = abs(float(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount') or 0))
            
            if name not in party_balances:
                party_balances[name] = 0
                
            if amt_type == '1': # Debit
                party_balances[name] += amt
            elif amt_type == '2': # Credit
                party_balances[name] -= amt

    parties = session.query(Party).all()
    updated = 0
    for p in parties:
        bname = p.name
        # The stored name in DB is upper cased in import, but AccDetail might be mixed.
        # But wait, in DB they are stored exactly as `party_name` which is normalized.
        # Let's normalize the same way.
        found_amt = party_balances.get(bname, 0)
        p.busy_closing_balance = found_amt
        updated += 1

    session.commit()
    print(f"Updated busy_closing_balance for {updated} parties.")

if __name__ == "__main__":
    files = sys.argv[1:]
    if not files:
        print("Please provide file paths")
        sys.exit(1)
        
    session = SessionLocal()
    for f in files:
        import_transactions(f, session)
        
    calculate_busy_balances(files, session)
    session.close()

import os
import sys
import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from decimal import Decimal
from datetime import datetime
from itertools import chain
from sqlalchemy import func

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.models import Party, Invoice, InvoiceItem, Payment, PaymentAllocation, JournalEntry, AccountMaster
from app.database import SessionLocal

def clean(value):
    return ' '.join((value or '').split()) or None

def parse_date(date_str):
    if not date_str:
        raise ValueError("missing date")
    try:
        return datetime.strptime(date_str, "%d-%m-%Y")
    except ValueError as exc:
        raise ValueError(f"invalid date {date_str!r}; expected DD-MM-YYYY") from exc


def parse_decimal(value, field_name):
    try:
        return Decimal(value or "0")
    except Exception as exc:
        raise ValueError(f"invalid {field_name}: {value!r}") from exc


def source_identity(element, voucher_type, file_path):
    """Return a stable identity for one source XML voucher."""
    payload = ET.tostring(element, encoding="utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:24]
    return f"BUSY:{os.path.basename(file_path)}:{voucher_type}:{digest}"

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


def import_transactions(file_path, session, created_by=1, report_path=None, commit=True):
    print(f"\n--- Reading {file_path} ---")
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return {"source": file_path, "imported": {}, "rejected": [{"type": "file", "reason": str(e)}]}

    report = {"source": file_path, "imported": {}, "rejected": [], "skipped": [], "unresolved_allocations": []}

    def reject(voucher_type, voucher, reason):
        report["rejected"].append({
            "type": voucher_type,
            "voucher": clean(voucher.findtext("VchNo")) if voucher is not None else None,
            "date": clean(voucher.findtext("Date")) if voucher is not None else None,
            "reason": reason,
        })

    def is_cancelled(voucher):
        return voucher.find('Cancelled') is not None

    def skip_cancelled(voucher_type, voucher):
        report['skipped'].append({
            'type': voucher_type,
            'voucher': clean(voucher.findtext('VchNo')),
            'date': clean(voucher.findtext('Date')),
            'reason': 'cancelled in BUSY',
        })

    def unresolved_allocation(voucher_type, voucher, ref_no):
        report['unresolved_allocations'].append({
            'type': voucher_type,
            'voucher': clean(voucher.findtext('VchNo')),
            'date': clean(voucher.findtext('Date')),
            'reference': ref_no,
            'reason': 'referenced bill was not imported',
        })

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
        name = ' '.join(name.split())
        if name in db_parties:
            return db_parties[name]
        new_party = Party(name=name, is_active=True, created_by=created_by)
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
        if is_cancelled(sale):
            skip_cancelled('Sale', sale)
            continue
        vch_no = clean(sale.findtext('VchNo'))
        date_str = clean(sale.findtext('Date'))
        party_tmpcode = sale.findtext('tmpMasterCode1')
        try:
            total_amt = parse_decimal(sale.findtext('tmpTotalAmt'), 'sale amount')
            inv_date = parse_date(date_str)
        except ValueError as exc:
            reject("Sale", sale, str(exc))
            continue
        
        party_name = account_map.get(party_tmpcode)
        if not party_name:
            party_name = clean(sale.findtext('MasterName1'))
            
        party_id = get_or_create_party(party_name)
        if not party_id:
            reject("Sale", sale, "missing debtor party")
            continue

        identity = source_identity(sale, "Sale", file_path)
        existing = session.query(Invoice).filter_by(description=identity).first()
        if existing:
            continue

        existing_number = session.query(Invoice).filter_by(
            invoice_number=vch_no, created_by=created_by
        ).first()
        if existing_number:
            if existing_number.party_id == party_id and existing_number.amount == total_amt:
                reject("Sale", sale, "duplicate invoice already exists")
            else:
                reject("Sale", sale, "invoice number already exists with different party or amount")
            continue
        
        invoice = Invoice(
            invoice_number=vch_no,
            party_id=party_id,
            created_by=created_by,
            amount=total_amt,
            balance_due=total_amt,
            invoice_date=inv_date,
            description=identity,
            is_paid=False,
            is_deleted=False
        )
        session.add(invoice)
        session.flush()
        
        # Line Items
        item_error = False
        item_entries = sale.find('ItemEntries')
        if item_entries is not None:
            for item_det in item_entries.findall('ItemDetail'):
                i_code = item_det.findtext('tmpItemCode')
                i_name = item_map.get(i_code)
                if not i_name:
                    i_name = clean(item_det.findtext('ItemName')) or "Unknown Item"
                
                try:
                    qty = parse_decimal(item_det.findtext('Qty') or '1', 'item quantity')
                    price = parse_decimal(item_det.findtext('Price'), 'item price')
                    amt = parse_decimal(item_det.findtext('Amt') or item_det.findtext('Amount'), 'item amount')
                except ValueError as exc:
                    reject("Sale", sale, str(exc))
                    session.delete(invoice)
                    session.flush()
                    item_error = True
                    break
                
                inv_item = InvoiceItem(
                    invoice_id=invoice.id,
                    item_name=i_name,
                    meter=qty,
                    rate=price,
                    total=amt
                )
                session.add(inv_item)
        if item_error:
            continue
        sales_added += 1

    report["imported"]["sales"] = sales_added
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
        if is_cancelled(rcpt):
            skip_cancelled('Receipt', rcpt)
            continue
        date_str = clean(rcpt.findtext('Date'))
        try:
            pay_date = parse_date(date_str)
        except ValueError as exc:
            reject("Receipt", rcpt, str(exc))
            continue
        
        acc_entries = rcpt.find('AccEntries')
        if acc_entries is None:
            reject("Receipt", rcpt, "missing account entries")
            continue
        
        # Collect all entries categorized
        debtor_entries = []
        contra_entries = []
        
        for acc_det in acc_entries.findall('AccDetail'):
            grp = acc_det.findtext('tmpGroupName') or ''
            amt_type = acc_det.findtext('AmountType')
            try:
                amt = parse_decimal(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount'), 'receipt amount')
            except ValueError as exc:
                reject("Receipt", rcpt, str(exc))
                debtor_entries = []
                break
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
            reject("Receipt", rcpt, "missing debtor entry")
            continue

        identity = source_identity(rcpt, "Receipt", file_path)
        if session.query(Payment).filter(Payment.note == identity).first():
            continue

        payment_mode = 'cash'
        for acc_det in acc_entries.findall('AccDetail'):
            group = acc_det.findtext('tmpGroupName') or ''
            if group in ('Bank Accounts', 'Bank (OD/CC)'):
                payment_mode = 'bank'
                break
            
        # Process each debtor entry in this receipt
        for deb in debtor_entries:
            acc_det = deb['acc_det']
            party_name = deb['name']
            pay_amount = deb['amt']
            
            if pay_amount <= 0:
                continue
                
            party_id = get_or_create_party(party_name)
            if not party_id:
                reject("Receipt", rcpt, "missing debtor party")
                continue

            # Calculate total discount (all contra entries in this receipt)
            discount = Decimal('0')
            for c in contra_entries:
                discount += c['amt']
            
            payment = Payment(
                party_id=party_id,
                created_by=created_by,
                amount=pay_amount,
                discount_amount=abs(discount) if len(debtor_entries) == 1 else Decimal('0'),
                unallocated=pay_amount,
                payment_date=pay_date,
                mode=payment_mode,
                note=identity,
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
                        
                    try:
                        alloc_amt = parse_decimal(val_str, 'receipt allocation')
                    except ValueError as exc:
                        reject("Receipt", rcpt, str(exc))
                        continue
                    if alloc_amt <= 0:
                        continue
                        
                    inv = session.query(Invoice).filter_by(invoice_number=ref_no, party_id=party_id).first()
                    if inv:
                        if alloc_amt > payment.unallocated or alloc_amt > inv.balance_due:
                            reject("Receipt", rcpt, f"allocation exceeds available balance for invoice {ref_no}")
                            continue
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
                    else:
                        unresolved_allocation("Receipt", rcpt, ref_no)

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
                        created_by=created_by,
                        amount=Decimal('0'),  # Zero impact on customer balance
                        contra_amount=Decimal(str(contra_amt)),  # For master account reporting
                        entry_date=pay_date,
                        description=f"Receipt Adj: {c['name']}"
                    )
                    session.add(j_entry)
                    contra_journals_added += 1

    report["imported"]["receipts"] = rcpts_added
    print(f"Receipts: Added {rcpts_added}")
    print(f"  Contra Journals (Discount/Dalali/etc.): Added {contra_journals_added}")
    
    # ---------------------------------------------------------
    # Import Journals, CrNotes, DbNotes
    # ---------------------------------------------------------
    print("4. Importing Journals & Notes...")
    jrnl_added = 0
    for jrnl in chain(root.findall('.//Journal'), root.findall('.//CrNote'), root.findall('.//DbNote')):
        if is_cancelled(jrnl):
            skip_cancelled(jrnl.tag, jrnl)
            continue
        date_str = clean(jrnl.findtext('Date'))
        voucher_type = jrnl.tag
        try:
            jrnl_date = parse_date(date_str)
        except ValueError as exc:
            reject(voucher_type, jrnl, str(exc))
            continue
        
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
            try:
                amt = parse_decimal(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount'), f'{voucher_type} amount')
            except ValueError as exc:
                reject(voucher_type, jrnl, str(exc))
                debtor_entries = []
                break
            
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
            reject(voucher_type, jrnl, "missing debtor entry")
            continue
            
        for deb in debtor_entries:
            acc_det = deb['acc_det']
            party_name = deb['name']
            
            if not party_name or party_name not in db_parties:
                reject(voucher_type, jrnl, "unknown debtor party")
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
                description=f"{source_identity(jrnl, voucher_type, file_path)}:{deb['code']}"
            ).first()
            if not j_entry:
                j_entry = JournalEntry(
                    party_id=party_id,
                    account_id=acct_id,
                    created_by=created_by,
                    amount=amt,
                    entry_date=jrnl_date,
                    description=f"{source_identity(jrnl, voucher_type, file_path)}:{deb['code']} | {contra_desc}"
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
                            try:
                                val = parse_decimal(bill_det.findtext('Value1'), f'{voucher_type} allocation')
                            except ValueError as exc:
                                reject(voucher_type, jrnl, str(exc))
                                continue
                            val = abs(val)
                            
                            invoice = session.query(Invoice).filter_by(party_id=party_id, invoice_number=ref_no).first()
                            if invoice:
                                if val > invoice.balance_due and amt_type == '2':
                                    reject(voucher_type, jrnl, f"allocation exceeds invoice balance: {ref_no}")
                                    continue
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

    report["imported"]["journals"] = jrnl_added
    print(f"Journals: Added {jrnl_added}")

    # ---------------------------------------------------------
    # Import Payments (Outgoing cash / Debits) as Journals
    # ---------------------------------------------------------
    print("4b. Importing Payments (Outgoing)...")
    pay_added = 0
    for out_pay in root.findall('.//Payment'):
        if is_cancelled(out_pay):
            skip_cancelled('Payment', out_pay)
            continue
        date_str = clean(out_pay.findtext('Date'))
        try:
            pay_date = parse_date(date_str)
        except ValueError as exc:
            reject("Payment", out_pay, str(exc))
            continue
        
        acc_entries = out_pay.find('AccEntries')
        if acc_entries is None:
            reject("Payment", out_pay, "missing account entries")
            continue
        found_debtor = False
        for acc_det in acc_entries.findall('AccDetail'):
            grp = acc_det.findtext('tmpGroupName') or ''
            if grp != 'Sundry Debtors':
                continue
            found_debtor = True
                
            acc_code = acc_det.findtext('tmpAccCode')
            party_name = account_map.get(acc_code)
            if not party_name:
                party_name = clean(acc_det.findtext('AccountName'))
                
            if not party_name or party_name not in db_parties:
                reject("Payment", out_pay, "unknown debtor party")
                continue
                
            party_id = db_parties[party_name]
            amt_type = acc_det.findtext('AmountType')
            try:
                amt = parse_decimal(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount'), 'payment amount')
            except ValueError as exc:
                reject("Payment", out_pay, str(exc))
                continue
            
            if amt <= 0:
                continue
                
            if amt_type == '2':
                amt = -amt
                
            j_entry = session.query(JournalEntry).filter_by(
                description=f"{source_identity(out_pay, 'Payment', file_path)}:{acc_code}"
            ).first()
            if not j_entry:
                session.add(JournalEntry(
                    party_id=party_id,
                    created_by=created_by,
                    amount=amt,
                    entry_date=pay_date,
                    description=f"{source_identity(out_pay, 'Payment', file_path)}:{acc_code} | Imported Outgoing Payment"
                ))
                pay_added += 1
        if not found_debtor:
            reject("Payment", out_pay, "missing debtor entry")

    report["imported"]["payments"] = pay_added
    print(f"Payments (Outgoing): Added {pay_added}")

    # ---------------------------------------------------------
    # Import Sale Returns
    # ---------------------------------------------------------
    print("5. Importing Sale Returns...")
    sr_added = 0
    for sr in root.findall('.//SaleReturn'):
        if is_cancelled(sr):
            skip_cancelled('SaleReturn', sr)
            continue
        vch_no = clean(sr.findtext('VchNo'))
        date_str = clean(sr.findtext('Date'))
        party_tmpcode = sr.findtext('tmpMasterCode1')
        try:
            total_amt = parse_decimal(sr.findtext('tmpTotalAmt'), 'sale return amount')
            sr_date = parse_date(date_str)
        except ValueError as exc:
            reject("SaleReturn", sr, str(exc))
            continue
        
        party_name = account_map.get(party_tmpcode)
        if not party_name:
            party_name = clean(sr.findtext('MasterName1'))
            
        party_id = get_or_create_party(party_name)
        if not party_id or total_amt <= 0:
            reject("SaleReturn", sr, "missing debtor party or non-positive amount")
            continue

        identity = source_identity(sr, "SaleReturn", file_path)
        j_entry = session.query(JournalEntry).filter_by(
            description=identity
        ).first()
        if not j_entry:
            j_entry = JournalEntry(
                party_id=party_id,
                created_by=created_by,
                amount=-total_amt,
                entry_date=sr_date,
                description=f"{identity} | Sale Return: {vch_no}"
            )
            session.add(j_entry)
            session.flush()
            sr_added += 1
            
            # Parse BillRefs for allocating against Invoices
            for bill_ref in sr.findall('.//PendingBillDetails/BillDetail/BillRefs'):
                method = bill_ref.findtext('Method')
                if method == '2':
                    ref_no = clean(bill_ref.findtext('RefNo'))
                    try:
                        val = parse_decimal(bill_ref.findtext('Value1'), 'sale return allocation')
                    except ValueError as exc:
                        reject("SaleReturn", sr, str(exc))
                        continue
                    val = abs(val)
                    
                    invoice = session.query(Invoice).filter_by(party_id=party_id, invoice_number=ref_no).first()
                    if invoice:
                        if val > invoice.balance_due:
                            reject("SaleReturn", sr, f"allocation exceeds invoice balance: {ref_no}")
                            continue
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
            
    report["imported"]["sale_returns"] = sr_added
    print(f"Sale Returns: Added {sr_added}")

    if commit:
        session.commit()
    if report_path:
        with open(report_path, 'w', encoding='utf-8') as output:
            json.dump(report, output, indent=2, default=str)
    print(f"Rejected: {len(report['rejected'])}")
    print(f"Skipped cancelled: {len(report['skipped'])}")
    print(f"Unresolved allocations: {len(report['unresolved_allocations'])}")
    for rejected in report['rejected']:
        print(
            f"  REJECTED {rejected['type']} {rejected.get('voucher') or '[no voucher number]'} "
            f"date={rejected.get('date') or '[missing]'}: {rejected['reason']}"
        )
    return report

def calculate_busy_balances(files, session, report_path=None, tolerance=Decimal('0.01')):
    from app.models import Party
    import glob
    print("\n--- Reconciling Constructed Balances Against BUSY Master ---")
    
    master_files = glob.glob('../*master*.DAT')
    
    party_balances = {}
    if master_files:
        master_file = master_files[0]
        print(f"Reading closing balances from: {master_file}")
        try:
            tree = ET.parse(master_file)
            root = tree.getroot()
            for acc in root.findall('.//Accounts/Account'):
                raw_name = acc.findtext('Name') or ''
                name = ' '.join(raw_name.split())
                if name:
                    # In BUSY, negative OPBal for Sundry Debtors means Debit (Due from customer)
                    opbal_str = acc.findtext('OPBal')
                    if opbal_str:
                        amt = -Decimal(opbal_str)
                        party_balances[name] = amt
        except Exception as e:
            print(f"Failed to parse master file: {e}")

    parties = session.query(Party).all()
    differences = []
    informational = []
    total_constructed = Decimal('0')
    total_busy = Decimal('0')
    for p in parties:
        bname = ' '.join(p.name.split())
        busy_balance = party_balances.get(bname)
        invoice_total = session.query(func.coalesce(func.sum(Invoice.amount), 0)).filter(
            Invoice.party_id == p.id, Invoice.is_deleted == False
        ).scalar()
        payment_total = session.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
            Payment.party_id == p.id, Payment.is_deleted == False
        ).scalar()
        journal_total = session.query(func.coalesce(func.sum(JournalEntry.amount), 0)).filter(
            JournalEntry.party_id == p.id, JournalEntry.is_deleted == False
        ).scalar()
        constructed_balance = Decimal(str(invoice_total or 0)) + Decimal(str(journal_total or 0)) - Decimal(str(payment_total or 0))

        if busy_balance is None:
            missing_record = {
                'party': p.name,
                'constructed_balance': str(constructed_balance),
                'busy_closing_balance': None,
                'difference': None,
                'status': 'MISSING_IN_MASTER',
            }
            if abs(constructed_balance) > tolerance:
                differences.append(missing_record)
            else:
                missing_record['status'] = 'MISSING_IN_MASTER_ZERO_BALANCE'
                informational.append(missing_record)
            continue

        difference = constructed_balance - busy_balance
        total_constructed += constructed_balance
        total_busy += busy_balance
        if abs(difference) > tolerance:
            differences.append({
                'party': p.name,
                'constructed_balance': str(constructed_balance),
                'busy_closing_balance': str(busy_balance),
                'difference': str(difference),
                'status': 'MISMATCH',
            })

    report = {
        'total_constructed': str(total_constructed),
        'total_busy_closing': str(total_busy),
        'total_difference': str(total_constructed - total_busy),
        'mismatch_count': len(differences),
        'informational_count': len(informational),
        'tolerance': str(tolerance),
        'differences': differences,
        'informational': informational,
    }
    if report_path:
        with open(report_path, 'w', encoding='utf-8') as output:
            json.dump(report, output, indent=2)
    print(f"Constructed total: {total_constructed:,.2f}")
    print(f"BUSY master total: {total_busy:,.2f}")
    print(f"Difference: {total_constructed - total_busy:,.2f}")
    print(f"Parties requiring review: {len(differences)}")
    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Import BUSY transactions with validation and rejection reporting.')
    parser.add_argument('files', nargs='+')
    parser.add_argument('--created-by', type=int, default=1)
    parser.add_argument('--report', help='Write a JSON report to this path.')
    parser.add_argument('--reconciliation-report', help='Write the constructed-vs-BUSY report to this path.')
    parser.add_argument('--allow-mismatch', action='store_true', help='Commit despite reconciliation differences.')
    args = parser.parse_args()
        
    session = SessionLocal()
    reports = []
    try:
        for f in args.files:
            reports.append(import_transactions(
                f, session, created_by=args.created_by, report_path=args.report, commit=False
            ))
        
        reconciliation = calculate_busy_balances(
            args.files, session, report_path=args.reconciliation_report
        )
        if args.report:
            combined_report = {
                'sources': reports,
                'rejected_count': sum(len(report.get('rejected', [])) for report in reports),
            }
            with open(args.report, 'w', encoding='utf-8') as output:
                json.dump(combined_report, output, indent=2, default=str)
        if reconciliation['mismatch_count'] and not args.allow_mismatch:
            session.rollback()
            print('Import rolled back: constructed balances do not match BUSY master balances.')
            sys.exit(2)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

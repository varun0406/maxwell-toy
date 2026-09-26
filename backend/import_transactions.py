import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.models import Party, Invoice, InvoiceItem, Payment
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
            continue # Skip if already exists
            
        amount_str = sale.findtext('tmpSalePurcAmt', '0')
        try:
            amount = Decimal(amount_str)
        except:
            amount = Decimal('0')
            
        invoice = Invoice(
            invoice_number=vch_no,
            party_id=party.id,
            created_by=1,
            amount=amount,
            balance_due=amount, # Unpaid initially
            invoice_date=parse_date(date_str),
            description="Sale"
        )
        session.add(invoice)
        session.flush() # get invoice.id
        invoices_added += 1
        
        # Add Invoice Items
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

    # 2. Import Sale Returns (SlRts) - As negative invoices or separate tracking
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
            
        amount_str = slrt.findtext('tmpSalePurcAmt', '0')
        try:
            amount = Decimal(amount_str)
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
        
        # In Receipts, the party is usually in AccEntries
        party = None
        amount = Decimal('0')
        
        # Find the Sundry Debtor account in AccEntries
        for acc in rcpt.findall('.//AccEntries/AccDetail'):
            grp = acc.findtext('tmpGroupName', '')
            if grp == 'Sundry Debtors':
                party_name = acc.findtext('AccountName', '')
                party = get_party(session, party_name)
                
                amt_str = acc.findtext('AmtMainCur', '0')
                try:
                    # Depending on Dr/Cr, amounts might be negative. Usually Cr is negative in BUSY for debtors.
                    # We want absolute amount for payment
                    amount = abs(Decimal(amt_str))
                except:
                    amount = Decimal('0')
                break
                
        if not party or amount == 0:
            continue
            
        payment = Payment(
            party_id=party.id,
            created_by=1,
            amount=amount,
            unallocated=amount, # Unallocated initially
            payment_date=parse_date(date_str),
            mode="Imported",
            note="Imported from TR.DAT"
        )
        session.add(payment)
        payments_added += 1

    session.commit()
    session.close()
    print(f"Import complete! Added {invoices_added} invoices/returns and {payments_added} payments.")

if __name__ == "__main__":
    import_transactions("../TR.DAT")

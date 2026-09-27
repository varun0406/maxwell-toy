import os
import sys
import argparse
import json
import xml.etree.ElementTree as ET

# Add the current directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.models import Party, JournalEntry, Invoice, AddressBook
from app.database import SessionLocal
from decimal import Decimal
from datetime import datetime, timezone

def clean(value):
    return ' '.join((value or '').split()) or None


def import_parties(file_path, created_by=1, include_suppliers=True, dry_run=False, report_path=None):
    print(f"Reading {file_path}...")
    
    # Check if the file starts with a root tag. If it's just a sequence of <Account> tags,
    # we might need to wrap it.
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except ET.ParseError:
        # Wrap in a dummy root if it fails
        print("Parsing failed. Trying to wrap in a dummy root tag...")
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = "<root>" + f.read() + "</root>"
        root = ET.fromstring(content)

    session = SessionLocal()
    
    added_count = 0
    updated_count = 0
    address_added = 0
    address_updated = 0
    skipped = []
    
    for account in root.findall('.//Account'):
        parent_group = account.findtext('ParentGroup', '')
        
        # We only want Sundry Debtors
        if parent_group != 'Sundry Debtors':
            if include_suppliers and parent_group == 'Sundry Creditors':
                name = clean(account.findtext('Name'))
                address_node = account.find('Address')
                if not name:
                    skipped.append({'type': 'supplier', 'reason': 'missing name'})
                    continue
                phone = clean((address_node.findtext('Mobile') if address_node is not None else None) or
                              (address_node.findtext('WhatsAppNo') if address_node is not None else None))
                address_line1 = clean(address_node.findtext('Address1') if address_node is not None else None)
                address_line2 = clean(address_node.findtext('Address2') if address_node is not None else None)
                city = clean((address_node.findtext('CityName') if address_node is not None else None) or
                             (address_node.findtext('Station') if address_node is not None else None) or
                             (address_node.findtext('StateName') if address_node is not None else None))
                if dry_run:
                    address_added += 1
                    continue
                existing_address = session.query(AddressBook).filter(AddressBook.name == name).first()
                if existing_address:
                    existing_address.phone = phone or existing_address.phone
                    existing_address.address_line1 = address_line1 or existing_address.address_line1
                    existing_address.address_line2 = address_line2 or existing_address.address_line2
                    existing_address.city = city or existing_address.city
                    address_updated += 1
                else:
                    session.add(AddressBook(name=name, phone=phone, address_line1=address_line1,
                                            address_line2=address_line2, city=city))
                    address_added += 1
            continue
            
        name = clean(account.findtext('Name'))
        if not name:
            continue
        if len(name) > 120:
            name = name[:120]
            
        broker_name = clean(account.findtext('BrokerName'))
        if broker_name and len(broker_name) > 120:
            broker_name = broker_name[:120]
        
        address_node = account.find('Address')
        phone = None
        gstin = None
        email = None
        addr1, addr2, addr3, city = None, None, None, None
        notes = ""
        
        if address_node is not None:
            mobile = clean(address_node.findtext('Mobile'))
            whatsapp = clean(address_node.findtext('WhatsAppNo'))
            phone = mobile or whatsapp
            # Truncate string fields to DB limits
            if phone and len(phone) > 20:
                phone = phone[:20]
                
            gstin = address_node.findtext('GSTNo', None)
            if gstin and len(gstin) > 20:
                gstin = gstin[:20]
                
            email = address_node.findtext('Email', None)
            if email and len(email) > 120:
                email = email[:120]
                
            addr1 = address_node.findtext('Address1', None)
            if addr1 and len(addr1) > 255:
                addr1 = addr1[:255]
                
            addr2 = address_node.findtext('Address2', None)
            if addr2 and len(addr2) > 255:
                addr2 = addr2[:255]
                
            addr3 = address_node.findtext('Address3', None)
            if addr3 and len(addr3) > 255:
                addr3 = addr3[:255]
            
            city_name = clean(address_node.findtext('CityName'))
            if city_name and city_name != '---Others---':
                city = city_name
            else:
                city = clean(address_node.findtext('Station'))
                if not city:
                    city = clean(address_node.findtext('Address4'))
                if not city:
                    city = clean(address_node.findtext('StateName'))
                    
            if city and len(city) > 120:
                city = city[:120]
                
            transport = address_node.findtext('Transport', '')
            if transport:
                notes = f"Transport: {transport}"
                
        if parent_group and len(parent_group) > 255:
            parent_group = parent_group[:255]
                
        # Check if party already exists
        existing = session.query(Party).filter(Party.name == name).first()
        
        if existing:
            # Update
            existing.phone = phone or existing.phone
            existing.agent_name = broker_name or existing.agent_name
            existing.billing_address_line1 = addr1 or existing.billing_address_line1
            existing.billing_address_line2 = addr2 or existing.billing_address_line2
            existing.billing_address_line3 = addr3 or existing.billing_address_line3
            existing.billing_city = city or existing.billing_city
            existing.gstin = gstin or existing.gstin
            existing.email = email or existing.email
            if notes and not existing.notes:
                existing.notes = notes
            party_record = existing
            updated_count += 1
        else:
            # Create new
            new_party = Party(
                name=name,
                phone=phone,
                agent_name=broker_name,
                billing_address_line1=addr1,
                billing_address_line2=addr2,
                billing_address_line3=addr3,
                billing_city=city,
                gstin=gstin,
                email=email,
                notes=notes,
                is_active=True,
                created_by=created_by
            )
            session.add(new_party)
            session.flush() # flush to get new_party.id
            party_record = new_party
            added_count += 1
            
        # Handle Opening Balance
        op_bal_str = account.findtext('OPBal', '0')
        try:
            op_bal = Decimal(op_bal_str)
        except:
            op_bal = Decimal('0')

        bill_detail_node = account.find('BillByBillDetail')
        has_bills = bill_detail_node is not None and list(bill_detail_node)

        if has_bills:
            # Import each individual prev-year bill as an Invoice
            for ref in bill_detail_node.findall('BillReference'):
                ref_no = ref.findtext('RefNo', '').strip()
                date_str = ref.findtext('Date', '')
                val_str = ref.findtext('Value1', '0')
                try:
                    # BUSY stores debtor amounts as negative; we store as positive (amount owed to us)
                    val = abs(Decimal(val_str))
                except:
                    continue

                if not ref_no or val == 0:
                    continue

                # IMPORTANT: Skip bills that will be imported as real transactions.
                # 25-26 and 26-27 vouchers come from BUSY 25-26.DAT and TR.DAT respectively.
                # Only create OB Invoices for bills older than 25-26 (e.g., 24-25 and before).
                ref_prefix = ref_no[:5]  # e.g. "25-26" or "24-25"
                if ref_prefix in ('25-26', '26-27'):
                    continue

                # Skip if already imported (e.g. duplicate run)
                existing_inv = session.query(Invoice).filter(Invoice.invoice_number == ref_no).first()
                if not existing_inv:
                    try:
                        inv_date = datetime.strptime(date_str, '%d-%m-%Y').replace(tzinfo=timezone.utc)
                    except:
                        inv_date = datetime(2026, 4, 1, tzinfo=timezone.utc)

                    session.add(Invoice(
                        invoice_number=ref_no,
                        party_id=party_record.id,
                        created_by=1,
                        amount=val,
                        balance_due=val,
                        invoice_date=inv_date,
                        description='Opening Balance Invoice'
                    ))

        elif op_bal != 0:
            # No individual bills → single lump-sum Journal Entry
            existing_je = session.query(JournalEntry).filter(
                JournalEntry.party_id == party_record.id,
                JournalEntry.description == 'Opening Balance'
            ).first()

            if not existing_je:
                # BUSY stores debtor OPBal as negative; negate so positive = amount owed to us
                session.add(JournalEntry(
                    party_id=party_record.id,
                    created_by=created_by,
                    amount=abs(op_bal),
                    entry_date=datetime(2026, 4, 1, tzinfo=timezone.utc),
                    description='Opening Balance'
                ))
            
    if dry_run:
        session.rollback()
    else:
        session.commit()
    session.close()
    report = {
        'source': file_path, 'dry_run': dry_run,
        'parties_added': added_count, 'parties_updated': updated_count,
        'supplier_addresses_added': address_added, 'supplier_addresses_updated': address_updated,
        'skipped': skipped,
    }
    print(json.dumps(report, indent=2))
    if report_path:
        with open(report_path, 'w', encoding='utf-8') as output:
            json.dump(report, output, indent=2)

if __name__ == "__main__":
    import sys as _sys
    # Support passing multiple files as CLI args, e.g.:
    #   python import_parties.py ../BUSY.DAT "../BUSY 25-26.DAT"
    # BUSY.DAT (current year) should come FIRST so its data takes priority.
    # BUSY 25-26.DAT (last year) fills in any parties that were active last year.
    parser = argparse.ArgumentParser(description='Import BUSY master parties and supplier addresses.')
    parser.add_argument('files', nargs='*', default=['../BUSY.DAT'])
    parser.add_argument('--created-by', type=int, default=1)
    parser.add_argument('--no-suppliers', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--report', help='Write a JSON import report to this path.')
    args = parser.parse_args()
    files = args.files
    for f in files:
        import_parties(f, created_by=args.created_by, include_suppliers=not args.no_suppliers,
                       dry_run=args.dry_run, report_path=args.report)

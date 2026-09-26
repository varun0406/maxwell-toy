import os
import sys
import xml.etree.ElementTree as ET
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the current directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.models import Party, JournalEntry, Invoice
from app.database import SessionLocal
from decimal import Decimal
from datetime import datetime, timezone

def import_parties(file_path):
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
    
    for account in root.findall('.//Account'):
        parent_group = account.findtext('ParentGroup', '')
        
        # We only want Sundry Debtors
        if parent_group != 'Sundry Debtors':
            continue
            
        name = account.findtext('Name', '')
        if not name:
            continue
        if len(name) > 120:
            name = name[:120]
            
        broker_name = account.findtext('BrokerName', None)
        if broker_name and len(broker_name) > 120:
            broker_name = broker_name[:120]
        
        address_node = account.find('Address')
        phone = None
        gstin = None
        addr1, addr2, addr3, city = None, None, None, None
        notes = ""
        
        if address_node is not None:
            mobile = address_node.findtext('Mobile', '')
            whatsapp = address_node.findtext('WhatsAppNo', '')
            phone = mobile if mobile else whatsapp
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
            
            city_name = address_node.findtext('CityName', '')
            if city_name and city_name != '---Others---':
                city = city_name
            else:
                city = address_node.findtext('Station', '')
                if not city:
                    city = address_node.findtext('Address4', '')
                if not city:
                    city = address_node.findtext('StateName', '')
                    
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
                created_by=1 # assuming admin user id 1
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
                    created_by=1,
                    amount=abs(op_bal),
                    entry_date=datetime(2026, 4, 1, tzinfo=timezone.utc),
                    description='Opening Balance'
                ))
            
    session.commit()
    session.close()
    print(f"Import complete! Added {added_count} and updated {updated_count} Sundry Debtors.")

if __name__ == "__main__":
    import sys as _sys
    # Support passing multiple files as CLI args, e.g.:
    #   python import_parties.py ../BUSY.DAT "../BUSY 25-26.DAT"
    # BUSY.DAT (current year) should come FIRST so its data takes priority.
    # BUSY 25-26.DAT (last year) fills in any parties that were active last year.
    files = _sys.argv[1:] if len(_sys.argv) > 1 else ["../BUSY.DAT"]
    for f in files:
        import_parties(f)

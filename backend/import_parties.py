import os
import sys
import xml.etree.ElementTree as ET
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the current directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.models import Party

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./maxwell_acc.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
        
        # We only want Sundry Debtors and Karigar
        if parent_group not in ['Sundry Debtors', 'Karigar', 'KARIGAR']:
            continue
            
        name = account.findtext('Name', '')
        if not name:
            continue
            
        broker_name = account.findtext('BrokerName', None)
        
        address_node = account.find('Address')
        phone = None
        gstin = None
        addr1, addr2, addr3, city = None, None, None, None
        notes = ""
        
        if address_node is not None:
            mobile = address_node.findtext('Mobile', '')
            whatsapp = address_node.findtext('WhatsAppNo', '')
            phone = mobile if mobile else whatsapp
            # If multiple numbers separated by comma, just take the first one or leave it
            # Schema allows string, so we can leave it as is if length < 255
            if phone and len(phone) > 100:
                phone = phone[:100]
                
            gstin = address_node.findtext('GSTNo', None)
            addr1 = address_node.findtext('Address1', None)
            addr2 = address_node.findtext('Address2', None)
            addr3 = address_node.findtext('Address3', None)
            
            city_name = address_node.findtext('CityName', '')
            if city_name and city_name != '---Others---':
                city = city_name
            else:
                city = address_node.findtext('Station', '')
                if not city:
                    city = address_node.findtext('Address4', '')
                if not city:
                    city = address_node.findtext('StateName', '')
                
            transport = address_node.findtext('Transport', '')
            if transport:
                notes = f"Transport: {transport}"
                
        # Check if party already exists
        existing = session.query(Party).filter(Party.name == name).first()
        
        if existing:
            # Update
            existing.phone = phone or existing.phone
            existing.agent_name = broker_name or existing.agent_name
            existing.billing_address_line1 = addr1 or existing.billing_address_line1
            existing.billing_address_line2 = addr2 or existing.billing_address_line2
            existing.billing_address_line3 = addr3 or existing.billing_address_line3
            existing.shipping_address_line1 = parent_group
            existing.billing_city = city or existing.billing_city
            existing.gstin = gstin or existing.gstin
            if notes and not existing.notes:
                existing.notes = notes
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
                shipping_address_line1=parent_group,
                billing_city=city,
                gstin=gstin,
                notes=notes,
                is_active=True,
                created_by=1 # assuming admin user id 1
            )
            session.add(new_party)
            added_count += 1
            
    session.commit()
    session.close()
    print(f"Import complete! Added {added_count} and updated {updated_count} Sundry Debtors.")

if __name__ == "__main__":
    import_parties("../MCMPL_20260924_MSAll.DAT")

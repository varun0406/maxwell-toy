import sys
sys.path.append('.')
from app.database import SessionLocal
from app.models import Invoice
import xml.etree.ElementTree as ET

session = SessionLocal()
tree = ET.parse('../BUSY 25-26.DAT')
root = tree.getroot()

skipped_dup = 0
missing_party = 0
good = 0

for sale in root.findall('.//Sales/Sale'):
    vch_no = sale.findtext('VchNo', '').strip()
    existing = session.query(Invoice).filter(Invoice.invoice_number == vch_no).first()
    if existing:
        skipped_dup += 1
        if skipped_dup <= 5:
            print(f"DUPLICATE SKIPPED: {vch_no} -> desc={existing.description}")
    else:
        good += 1

print(f"\nTotal Sales in XML   : {len(root.findall('.//Sales/Sale'))}")
print(f"Skipped (duplicate)  : {skipped_dup}")
print(f"Would be imported    : {good}")

# Check how many OB invoices overlap with 25-26 sale vch numbers
ob_invs = session.query(Invoice).filter(Invoice.description == 'Opening Balance Invoice').count()
print(f"\nOpening Balance Invoices in DB: {ob_invs}")
session.close()

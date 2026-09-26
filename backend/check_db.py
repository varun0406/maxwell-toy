import sys
sys.path.append('.')
from app.database import SessionLocal
from app.models import Party, Invoice, JournalEntry
import xml.etree.ElementTree as ET
from decimal import Decimal

session = SessionLocal()

# The BillByBillDetail invoices are 0 - means they weren't created
# Let's check why - check if BillByBillDetail is being parsed from BUSY.DAT
tree = ET.parse('../BUSY.DAT')
root = tree.getroot()

with_bb = 0
total_refs = 0
for acc in root.findall('.//Account'):
    if acc.findtext('ParentGroup','') == 'Sundry Debtors':
        bb = acc.find('BillByBillDetail')
        if bb is not None and list(bb):
            with_bb += 1
            refs = bb.findall('BillReference')
            total_refs += len(refs)
            
print(f"Accounts with BillByBillDetail in BUSY.DAT: {with_bb}")
print(f"Total BillReferences (prev-year invoices)  : {total_refs}")
print()
print("Sample party:")
for acc in root.findall('.//Account'):
    if acc.findtext('ParentGroup','') == 'Sundry Debtors':
        bb = acc.find('BillByBillDetail')
        if bb is not None and list(bb):
            print(f"  Party: {acc.findtext('Name')}")
            for ref in bb.findall('BillReference')[:2]:
                print(f"    RefNo: {ref.findtext('RefNo')}, Value1: {ref.findtext('Value1')}, Date: {ref.findtext('Date')}")
            break
            
# Check how many OB invoices we actually have in DB
ob_invs = session.query(Invoice).filter(Invoice.description == 'Opening Balance Invoice').count()
print(f"\nOpening Balance Invoices in DB: {ob_invs}")
# Also check journal entries for opening balance
ob_jes = session.query(JournalEntry).filter(JournalEntry.description == 'Opening Balance').count()
print(f"Opening Balance Journal Entries in DB: {ob_jes}")

session.close()

import xml.etree.ElementTree as ET
import sys
from decimal import Decimal

files = [
    '/home/varun/Documents/maxwellMobAcc/busy-24-25a.DAT',
    '/home/varun/Documents/maxwellMobAcc/busy-25-26..DAT',
    '/home/varun/Documents/maxwellMobAcc/busy 26-27....DAT'
]

def clean(val):
    return ' '.join((val or '').split())

def is_deepak(name):
    if not name: return False
    n = name.upper()
    return 'DEEPAK' in n and 'BHAVNAGAR' in n

totals = {
    'Sales': Decimal('0'),
    'Receipts': Decimal('0'),
    'SaleReturns': Decimal('0'),
    'Journals': Decimal('0'),
    'Payments': Decimal('0')
}

details = []

account_map = {}

for file in files:
    try:
        tree = ET.parse(file)
        root = tree.getroot()
        
        # Build account map
        for acc in root.findall('.//AccountMaster'):
            code = clean(acc.findtext('MasterCode'))
            code1 = clean(acc.findtext('tmpMasterCode1'))
            name = clean(acc.findtext('Name'))
            if code and name: account_map[code] = name
            if code1 and name: account_map[code1] = name
            
        def get_party_name(element):
            name1 = clean(element.findtext('MasterName1'))
            if name1: return name1
            name2 = clean(element.findtext('AccountName'))
            if name2: return name2
            code1 = clean(element.findtext('MasterCode1'))
            if code1 and code1 in account_map: return account_map[code1]
            tcode1 = clean(element.findtext('tmpMasterCode1'))
            if tcode1 and tcode1 in account_map: return account_map[tcode1]
            tcode = clean(element.findtext('tmpAccCode'))
            if tcode and tcode in account_map: return account_map[tcode]
            return None

        # 1. Sales
        for v in root.findall('.//Sale'):
            if v.find('Cancelled') is not None: continue
            party = get_party_name(v)
            if party and is_deepak(party):
                amt = Decimal(clean(v.findtext('tmpTotalAmt')) or '0')
                totals['Sales'] += amt
                details.append(('Sale', clean(v.findtext('Date')), clean(v.findtext('VchNo')), amt))
                
        # 2. Sale Returns
        for v in root.findall('.//SaleReturn'):
            if v.find('Cancelled') is not None: continue
            party = get_party_name(v)
            if party and is_deepak(party):
                amt = Decimal(clean(v.findtext('tmpTotalAmt')) or '0')
                totals['SaleReturns'] += amt
                details.append(('SaleReturn', clean(v.findtext('Date')), clean(v.findtext('VchNo')), amt))
                
        # 3. Receipts
        for v in root.findall('.//Receipt'):
            if v.find('Cancelled') is not None: continue
            for acc in v.findall('.//AccDetail'):
                party = get_party_name(acc)
                if party and is_deepak(party):
                    amt = Decimal(clean(acc.findtext('AmtMainCur')) or '0')
                    totals['Receipts'] += amt
                    details.append(('Receipt', clean(acc.findtext('Date')), clean(v.findtext('VchNo')), amt))
                    
        # 4. Payments (Outgoing)
        for v in root.findall('.//Payment'):
            if v.find('Cancelled') is not None: continue
            for acc in v.findall('.//AccDetail'):
                party = get_party_name(acc)
                if party and is_deepak(party):
                    amt = Decimal(clean(acc.findtext('AmtMainCur')) or '0')
                    totals['Payments'] += amt
                    details.append(('Payment_Out', clean(acc.findtext('Date')), clean(v.findtext('VchNo')), amt))

        # 5. Journals
        for v in root.findall('.//Journal'):
            if v.find('Cancelled') is not None: continue
            for acc in v.findall('.//AccDetail'):
                party = get_party_name(acc)
                if party and is_deepak(party):
                    amt = Decimal(clean(acc.findtext('AmtMainCur')) or '0')
                    # AmountType: 1 = Debit, 2 = Credit
                    atype = clean(acc.findtext('AmountType'))
                    if atype == '1': # Debit
                        totals['Journals'] += amt
                        details.append(('Journal_Dr', clean(acc.findtext('Date')), clean(v.findtext('VchNo')), amt))
                    elif atype == '2': # Credit
                        totals['Journals'] -= amt
                        details.append(('Journal_Cr', clean(acc.findtext('Date')), clean(v.findtext('VchNo')), -amt))

    except Exception as e:
        print(f"Error in {file}: {e}")

print(f"--- XML Raw Extracted Totals for DEEPAKBHAI BHAVNAGAR ---")
print(f"Total Sales: {totals['Sales']}")
print(f"Total Receipts: {totals['Receipts']}")
print(f"Total Sale Returns: {totals['SaleReturns']}")
print(f"Total Payments (Outgoing): {totals['Payments']}")
print(f"Total Journals (Net Debit): {totals['Journals']}")

net_outstanding = totals['Sales'] - totals['Receipts'] - totals['SaleReturns'] + totals['Payments'] + totals['Journals']
print(f"--- XML Calculated Net Outstanding: {net_outstanding} ---")

# Compare with our DB
from app.database import SessionLocal
from app.models import Party, Invoice, Payment, JournalEntry
db = SessionLocal()
party = db.query(Party).filter(Party.name.ilike('%Deepakbhai%Bhavnagar%')).first()
if party:
    db_sales = sum(i.amount for i in party.invoices)
    db_receipts = sum(p.amount for p in party.payments)
    db_journals = sum(j.amount for j in party.journal_entries)
    
    print("\n--- DB Extracted Totals ---")
    print(f"Total Invoiced (Sales): {db_sales}")
    print(f"Total Payments (Receipts): {db_receipts}")
    print(f"Total Journals (including returns/payments): {db_journals}")
    
    db_net = db_sales - db_receipts + db_journals
    print(f"--- DB Calculated Net Outstanding: {db_net} ---")
else:
    print("Party not found in DB!")

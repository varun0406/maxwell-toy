import xml.etree.ElementTree as ET
from decimal import Decimal

tree = ET.parse('BUSY 25-26.DAT')
root = tree.getroot()

found = 0
for rcpt in root.findall('.//Rcpts/Receipt'):
    party = None
    amount = Decimal('0')
    
    for acc in rcpt.findall('.//AccEntries/AccDetail'):
        name = acc.findtext('AccountName', '').strip()
        amt_str = acc.findtext('AmtMainCur', '0')
        amt = abs(Decimal(amt_str) if amt_str else 0)
        
        if acc.findtext('AmountType') == '2' and name.lower() not in ['cash', 'bank', 'discount']:
            party = name
            amount = amt
            
    if not party or amount == 0:
        print(f"\n--- EMPTY/BLANK RECEIPT RECORD #{found+1} ---")
        xml_str = ET.tostring(rcpt, encoding='unicode')
        # Pretty print a bit manually or just show raw
        print(xml_str)
        found += 1
        if found >= 3:
            break

print(f"\n(Showing first {found} of the 22 empty records found in BUSY 25-26.DAT)")

import xml.etree.ElementTree as ET
from decimal import Decimal

def parse_date(d):
    if not d: return ""
    try:
        parts = d.split('-')
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except:
        pass
    return d

tree = ET.parse('BUSY26-27..DAT')
root = tree.getroot()

receipts = root.findall('.//Rcpts/Receipt')
print(f"Total receipts: {len(receipts)}")

seen = set()
duplicates = []
invalid = []

for rcpt in receipts:
    date_str = rcpt.findtext('Date', '')
    p_date = parse_date(date_str)
    
    party = None
    amount = Decimal('0')
    mode = 'cash'
    
    for acc in rcpt.findall('.//AccEntries/AccDetail'):
        name = acc.findtext('AccountName', '').strip()
        amt_str = acc.findtext('AmtMainCur', '0')
        amt = abs(Decimal(amt_str) if amt_str else 0)
        
        if acc.findtext('AmountType') == '2':
            if name.lower() not in ['cash', 'bank', 'discount']:
                party = name
                amount = amt
        elif acc.findtext('AmountType') == '1':
            if 'bank' in name.lower() or 'neft' in name.lower() or 'rtgs' in name.lower():
                mode = 'bank'
                
    vch_other = rcpt.find('VchOtherInfoDetails')
    nar1 = ""
    nar2 = ""
    if vch_other is not None:
        nar1 = vch_other.findtext('Narration1', '').strip()
        nar2 = vch_other.findtext('Narration2', '').strip()
    note = f"{nar1} {nar2}".strip()
    
    if not party or amount == 0:
        invalid.append({'party': party, 'amount': amount, 'date': date_str, 'note': note})
        continue
        
    key = (party, amount, p_date, note)
    if key in seen:
        duplicates.append(key)
    else:
        seen.add(key)

print(f"Invalid (Zero amount or no party): {len(invalid)}")
for inv in invalid:
    print("  ", inv)

print(f"\nDuplicates within file: {len(duplicates)}")
for dup in duplicates:
    print("  ", dup)


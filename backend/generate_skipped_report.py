import xml.etree.ElementTree as ET
from decimal import Decimal

files = ['BUSY 24-25.DAT', 'BUSY 25-26.DAT', 'BUSY26-27..DAT']
db_invoices = set()

for file in files:
    try:
        tree = ET.parse(file)
        root = tree.getroot()
    except Exception as e:
        print(f"Error reading {file}: {e}")
        continue
        
    print(f"\n--- {file} ---")
    skipped_sales = 0
    skipped_receipts = 0
    
    for sale in root.findall('.//Sales/Sale'):
        vch_no = sale.findtext('VchNo', '').strip()
        party_name = sale.findtext('MasterName1', '').strip()
        
        if not party_name:
            print(f"Skipping Sale {vch_no}: Missing Party")
            skipped_sales += 1
        elif vch_no in db_invoices:
            print(f"Skipping Sale {vch_no}: Already in DB (from an earlier file or earlier in this file)")
            skipped_sales += 1
        else:
            db_invoices.add(vch_no)
            
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
            date_str = rcpt.findtext('Date', '')
            print(f"Skipping Receipt on {date_str}: Party='{party}', Amount={amount}")
            skipped_receipts += 1
            
    print(f"Total Skipped Sales in {file}: {skipped_sales}")
    print(f"Total Skipped Receipts in {file}: {skipped_receipts}")


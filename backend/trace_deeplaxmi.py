import xml.etree.ElementTree as ET

party = 'DEEPLAXMI GARMENTS'
print(f"--- Tracing Transactions for {party} ---")

files = ['../busy(24-25).DAT', '../busy(25-26).DAT', '../busy(26-27).DAT']
total_debits = 0
total_credits = 0

for f in files:
    print(f"\nYear: {f}")
    tree = ET.parse(f)
    debits = 0
    credits = 0
    for acc_det in tree.getroot().findall('.//AccDetail'):
        name = ' '.join((acc_det.findtext('AccountName') or '').split())
        if name == party:
            amt_type = acc_det.findtext('AmountType')
            amt = abs(float(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount') or 0))
            if amt_type == '1': 
                debits += amt
            elif amt_type == '2': 
                credits += amt
    
    print(f"  Debits:  {debits:,.2f}")
    print(f"  Credits: {credits:,.2f}")
    print(f"  Net for Year: {debits - credits:,.2f}")
    
    total_debits += debits
    total_credits += credits

print("\n--- Grand Totals ---")
print(f"Total Debits (All Years): {total_debits:,.2f}")
print(f"Total Credits (All Years): {total_credits:,.2f}")
print(f"Calculated DB Balance: {total_debits - total_credits:,.2f}")

tree = ET.parse('../busy(26-27)master.DAT')
for acc in tree.getroot().findall('.//Accounts/Account'):
    name = ' '.join((acc.findtext('Name') or '').split())
    if name == party:
        opbal_str = acc.findtext('OPBal')
        if opbal_str:
            opbal2026 = -float(opbal_str)
            print(f"\nBUSY Master OPBal (April 2026): {opbal2026:,.2f}")
            print(f"Calculated Balance up to April 2026: {(total_debits - total_credits) - (debits - credits):,.2f}")
            print(f"Discrepancy in April 2026 Opening Balance: {opbal2026 - ((total_debits - total_credits) - (debits - credits)):,.2f}")


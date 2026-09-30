import xml.etree.ElementTree as ET

party_name = 'RAJA BHAI(SURAT)'
files = ['../BUSY 24-25.DAT', '../BUSY 25-26.DAT', '../BUSY26-27..DAT']

debits = 0
credits = 0
for f in files:
    tree = ET.parse(f)
    root = tree.getroot()
    for acc_det in root.findall('.//AccDetail'):
        name = ' '.join((acc_det.findtext('AccountName') or '').split())
        if name != party_name:
            continue
            
        amt_type = acc_det.findtext('AmountType')
        amt = abs(float(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount') or 0))
        
        if amt_type == '1': # Debit
            debits += amt
        elif amt_type == '2': # Credit
            credits += amt

print(f"BUSY Debits (+): {debits:,.2f}")
print(f"BUSY Credits (-): {credits:,.2f}")
print(f"BUSY Net: {debits - credits:,.2f}")

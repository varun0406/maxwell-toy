import xml.etree.ElementTree as ET

party = 'DEEPLAXMI GARMENTS'
tree = ET.parse('../busy(26-27).DAT')

debits = []
for acc_det in tree.getroot().findall('.//AccDetail'):
    name = ' '.join((acc_det.findtext('AccountName') or '').split())
    if name == party:
        amt_type = acc_det.findtext('AmountType')
        amt = abs(float(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount') or 0))
        if amt_type == '1':
            debits.append(amt)

print(f"All Debits in 26-27 for DEEPLAXMI:")
for p in debits:
    print(f"  {p:,.2f}")

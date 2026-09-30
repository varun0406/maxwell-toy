import xml.etree.ElementTree as ET
party_name = ' '.join('SAJANBHAI ( V I P )'.split())
f = '../busy(24-25).DAT'

debits = 0
credits = 0
tree = ET.parse(f)
root = tree.getroot()
for acc_det in root.findall('.//AccDetail'):
    name = ' '.join((acc_det.findtext('AccountName') or '').split())
    if name != party_name:
        continue
    amt_type = acc_det.findtext('AmountType')
    amt = abs(float(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount') or 0))
    if amt_type == '1': debits += amt
    elif amt_type == '2': credits += amt

print(f"24-25 Net for SAJANBHAI: {debits - credits:,.2f}")

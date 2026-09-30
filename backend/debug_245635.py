import xml.etree.ElementTree as ET

party = 'DEEPLAXMI GARMENTS'
print(f"--- Checking for 245,635 in {party} ---")

tree = ET.parse('../busy(26-27).DAT')
for acc_det in tree.getroot().findall('.//AccDetail'):
    name = ' '.join((acc_det.findtext('AccountName') or '').split())
    if name == party:
        amt = abs(float(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount') or 0))
        if amt == 245635.0 or amt == 245635:
            print(f"Found EXACT match of 245,635 in 26-27 transactions!")
            print(f"  VchNo: {acc_det.findtext('VchNo')}")
            print(f"  AmountType: {acc_det.findtext('AmountType')}")

# Sum of all payments to see if we can find a combination
payments = []
for acc_det in tree.getroot().findall('.//AccDetail'):
    name = ' '.join((acc_det.findtext('AccountName') or '').split())
    if name == party:
        amt_type = acc_det.findtext('AmountType')
        amt = abs(float(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount') or 0))
        if amt_type == '2':
            payments.append(amt)

print(f"\nAll Credits in 26-27 for DEEPLAXMI:")
for p in payments:
    print(f"  {p:,.2f}")

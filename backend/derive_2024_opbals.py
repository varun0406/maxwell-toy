import xml.etree.ElementTree as ET

# 1. Get net transactions for 24-25
net_24_25 = {}
tree = ET.parse('../busy(24-25).DAT')
for acc_det in tree.getroot().findall('.//AccDetail'):
    name = ' '.join((acc_det.findtext('AccountName') or '').split())
    amt_type = acc_det.findtext('AmountType')
    amt = abs(float(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount') or 0))
    if name not in net_24_25:
        net_24_25[name] = 0
    if amt_type == '1': net_24_25[name] += amt
    elif amt_type == '2': net_24_25[name] -= amt

# 2. Get OPBal from 25-26
opbal_25_26 = {}
tree2 = ET.parse('../busy(25-26).DAT')
for acc in tree2.getroot().findall('.//Accounts/Account'):
    name = acc.findtext('Name')
    if name:
        opbal_str = acc.findtext('OPBal')
        if opbal_str:
            normalized_name = ' '.join(name.split())
            opbal_25_26[normalized_name] = -float(opbal_str)

# 3. Derive 24-25 OPBal
opbal_24_25 = {}
for name, op25 in opbal_25_26.items():
    net24 = net_24_25.get(name, 0)
    op24 = op25 - net24
    opbal_24_25[name] = op24

print(f"Derived Opening Balances for {len(opbal_24_25)} parties.")
print(f"Example SAJANBHAI: {opbal_24_25.get('SAJANBHAI ( V I P )')}")
print(f"Example DEEPLAXMI: {opbal_24_25.get('DEEPLAXMI GARMENTS')}")
print(f"Example MAHADEV: {opbal_24_25.get('MAHADEV JIGNESHBHAI (BHAVNAGAR)')}")

# Count how many are non-zero
nonzero = {k: v for k, v in opbal_24_25.items() if abs(v) > 0.01}
print(f"Non-zero opening balances: {len(nonzero)}")
for k, v in list(nonzero.items())[:10]:
    print(f"  {k}: {v}")

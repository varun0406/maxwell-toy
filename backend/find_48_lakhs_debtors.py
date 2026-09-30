import xml.etree.ElementTree as ET

net_24_26 = {}
for f in ['../busy(24-25).DAT', '../busy(25-26).DAT']:
    tree = ET.parse(f)
    for acc_det in tree.getroot().findall('.//AccDetail'):
        raw_name = acc_det.findtext('AccountName') or ''
        name = ' '.join(raw_name.split())
        amt_type = acc_det.findtext('AmountType')
        amt = abs(float(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount') or 0))
        if name not in net_24_26:
            net_24_26[name] = 0
        if amt_type == '1': net_24_26[name] += amt
        elif amt_type == '2': net_24_26[name] -= amt

debtors_missing = 0
creditors_missing = 0

tree = ET.parse('../busy(26-27)master.DAT')
for acc in tree.getroot().findall('.//Accounts/Account'):
    grp = acc.findtext('ParentGroup')
    if grp in ['Sundry Debtors', 'Sundry Creditors']:
        name = acc.findtext('Name')
        if name:
            name = ' '.join(name.split())
            opbal_str = acc.findtext('OPBal')
            if opbal_str:
                opbal2026 = -float(opbal_str)
                net_transactions = net_24_26.get(name, 0)
                op2024 = opbal2026 - net_transactions
                if abs(op2024) > 0.01:
                    if grp == 'Sundry Debtors':
                        debtors_missing += op2024
                    else:
                        creditors_missing += op2024

print(f"Missing Sundry Debtors Opening Balance: {debtors_missing:,.2f}")
print(f"Missing Sundry Creditors Opening Balance: {creditors_missing:,.2f}")


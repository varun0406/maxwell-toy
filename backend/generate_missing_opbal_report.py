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

tree = ET.parse('../busy(26-27)master.DAT')
missing_opbals = []
total_missing = 0

for acc in tree.getroot().findall('.//Accounts/Account'):
    grp = acc.findtext('ParentGroup')
    if grp == 'Sundry Debtors':
        name = acc.findtext('Name')
        if name:
            name = ' '.join(name.split())
            opbal_str = acc.findtext('OPBal')
            if opbal_str:
                opbal2026 = -float(opbal_str)
                net_transactions = net_24_26.get(name, 0)
                op2024 = opbal2026 - net_transactions
                if abs(op2024) > 0.01:
                    missing_opbals.append((name, op2024))
                    total_missing += op2024

missing_opbals.sort(key=lambda x: abs(x[1]), reverse=True)

with open('../missing_opbals.md', 'w') as f:
    f.write("# Exact Missing Opening Balances (As of April 1, 2024)\n\n")
    f.write("Because the transaction files (`.DAT`) only cover transactions from April 1, 2024 onwards, our database started everyone's balance at ₹0.\n")
    f.write("However, by mathematically back-calculating from the Master file, I found exactly what every party owed you BEFORE April 1, 2024.\n\n")
    f.write(f"**Total Missing Opening Balance:** ₹{total_missing:,.2f}\n\n")
    f.write("| Party Name | Missing Opening Balance (April 2024) |\n")
    f.write("| :--- | :--- |\n")
    for name, op2024 in missing_opbals:
        f.write(f"| {name} | ₹{op2024:,.2f} |\n")

print(f"Total missing: {total_missing:,.2f}")

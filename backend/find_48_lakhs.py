import xml.etree.ElementTree as ET

# 1. Sum up all Net Transactions in 24-25 and 25-26
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
            
        if amt_type == '1': # Debit
            net_24_26[name] += amt
        elif amt_type == '2': # Credit
            net_24_26[name] -= amt

# 2. Get OPBal as of April 1, 2026 from the Master file
opbal_2026 = {}
tree = ET.parse('../busy(26-27)master.DAT')
for acc in tree.getroot().findall('.//Accounts/Account'):
    name = acc.findtext('Name')
    if name:
        name = ' '.join(name.split())
        opbal_str = acc.findtext('OPBal')
        if opbal_str:
            # In BUSY, negative OPBal for Sundry Debtors means Debit (Due from customer)
            opbal_2026[name] = -float(opbal_str)

# 3. Calculate Opening Balance as of April 1, 2024
total_missing_2024_opbal = 0
parties_with_missing_opbal = []

for name, op2026 in opbal_2026.items():
    net_transactions = net_24_26.get(name, 0)
    op2024 = op2026 - net_transactions
    
    if abs(op2024) > 0.01:
        total_missing_2024_opbal += op2024
        parties_with_missing_opbal.append((name, op2024))

print(f"Total Missing Opening Balance (as of April 1, 2024): {total_missing_2024_opbal:,.2f}")
print(f"Number of parties with missing Opening Balances: {len(parties_with_missing_opbal)}")

parties_with_missing_opbal.sort(key=lambda x: abs(x[1]), reverse=True)
print("\nTop 10 Parties missing Opening Balances:")
for p in parties_with_missing_opbal[:10]:
    print(f"{p[0]}: {p[1]:,.2f}")


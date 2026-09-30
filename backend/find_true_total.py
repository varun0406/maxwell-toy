import xml.etree.ElementTree as ET

net_26_27 = {}
tree = ET.parse('../busy(26-27).DAT')
for acc_det in tree.getroot().findall('.//AccDetail'):
    raw_name = acc_det.findtext('AccountName') or ''
    name = ' '.join(raw_name.split())
    amt_type = acc_det.findtext('AmountType')
    amt = abs(float(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount') or 0))
    if name not in net_26_27:
        net_26_27[name] = 0
    if amt_type == '1': net_26_27[name] += amt
    elif amt_type == '2': net_26_27[name] -= amt

tree = ET.parse('../busy(26-27)master.DAT')
true_closing_balance = 0
calculated_db_balance = 0 # What our DB calculates (which doesn't have OPBals from 2024)

# Need the full 3 years for calculated_db_balance
full_3_years_net = {}
for f in ['../busy(24-25).DAT', '../busy(25-26).DAT', '../busy(26-27).DAT']:
    t = ET.parse(f)
    for acc_det in t.getroot().findall('.//AccDetail'):
        raw_name = acc_det.findtext('AccountName') or ''
        name = ' '.join(raw_name.split())
        amt_type = acc_det.findtext('AmountType')
        amt = abs(float(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount') or 0))
        if name not in full_3_years_net:
            full_3_years_net[name] = 0
        if amt_type == '1': full_3_years_net[name] += amt
        elif amt_type == '2': full_3_years_net[name] -= amt

for acc in tree.getroot().findall('.//Accounts/Account'):
    grp = acc.findtext('ParentGroup')
    if grp == 'Sundry Debtors':
        name = acc.findtext('Name')
        if name:
            name = ' '.join(name.split())
            opbal_str = acc.findtext('OPBal')
            
            # The true final balance is OPBal (from start of 26-27) + Net of 26-27 transactions!
            opbal2026 = 0
            if opbal_str:
                opbal2026 = -float(opbal_str)
                
            final_party_balance = opbal2026 + net_26_27.get(name, 0)
            true_closing_balance += final_party_balance
            
            calculated_db_balance += full_3_years_net.get(name, 0)

print(f"True Total Sundry Debtors (including OPBals): {true_closing_balance:,.2f}")
print(f"Our DB Calculated Total (missing OPBals): {calculated_db_balance:,.2f}")
print(f"Difference: {true_closing_balance - calculated_db_balance:,.2f}")

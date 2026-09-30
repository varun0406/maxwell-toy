import xml.etree.ElementTree as ET

party_name = 'RAJA BHAI(SURAT)'
files = ['../BUSY 24-25.DAT', '../BUSY 25-26.DAT', '../BUSY26-27..DAT']

print(f"--- TRANSACTIONS FOR {party_name} IN BUSY ---")
total_due = 0
for f in files:
    tree = ET.parse(f)
    root = tree.getroot()
    for acc_det in root.findall('.//AccDetail'):
        name = ' '.join((acc_det.findtext('AccountName') or '').split())
        if name != party_name:
            continue
            
        amt_type = acc_det.findtext('AmountType')
        amt = abs(float(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount') or 0))
        
        # Go up to the voucher to see what it is
        vouch = acc_det.find('../../..')
        vch_type = vouch.findtext('VchType') if vouch else 'Unknown'
        vch_no = vouch.findtext('VchNo') if vouch else 'Unknown'
        vch_date = vouch.findtext('Date') if vouch else 'Unknown'
        
        if amt_type == '1': # Debit (Increase Due)
            total_due += amt
            print(f"[{vch_date}] {vch_type} {vch_no} | DEBIT  | +{amt:,.2f}")
        elif amt_type == '2': # Credit (Decrease Due)
            total_due -= amt
            print(f"[{vch_date}] {vch_type} {vch_no} | CREDIT | -{amt:,.2f}")

print(f"\nFinal Expected Balance: {total_due:,.2f}")

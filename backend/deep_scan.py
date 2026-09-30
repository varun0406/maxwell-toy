import xml.etree.ElementTree as ET
from collections import defaultdict

files = ['../BUSY 24-25.DAT', '../BUSY 25-26.DAT', '../BUSY26-27..DAT']

# 1. Find ALL unique contra accounts used alongside Sundry Debtors
contra_accounts = defaultdict(lambda: {'count': 0, 'total_debit': 0, 'total_credit': 0, 'voucher_types': set()})

# 2. Cross-party settlements (one debtor credited, another debtor debited in same voucher)
cross_party = []

# 3. All voucher types and their structures
voucher_structures = defaultdict(lambda: {'count': 0, 'has_debtor': 0, 'sample': None})

for f in files:
    tree = ET.parse(f)
    root = tree.getroot()
    
    for elem in root:
        tag = elem.tag
        if not isinstance(tag, str):
            continue
            
        voucher_structures[tag]['count'] += 1
        
        acc_entries = elem.find('AccEntries')
        if acc_entries is None:
            continue
        
        debtors_in_voucher = []
        non_debtors_in_voucher = []
        
        for acc_det in acc_entries.findall('AccDetail'):
            grp = acc_det.findtext('tmpGroupName') or ''
            name = acc_det.findtext('AccountName') or ''
            amt_type = acc_det.findtext('AmountType')
            amt = float(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount') or '0')
            
            if grp == 'Sundry Debtors':
                debtors_in_voucher.append({'name': name, 'type': amt_type, 'amt': amt})
            else:
                non_debtors_in_voucher.append({'name': name, 'group': grp, 'type': amt_type, 'amt': amt})
        
        if debtors_in_voucher:
            voucher_structures[tag]['has_debtor'] += 1
            if voucher_structures[tag]['sample'] is None:
                voucher_structures[tag]['sample'] = ET.tostring(elem, encoding='unicode')[:2000]
            
            # Track contra accounts
            for nd in non_debtors_in_voucher:
                key = f"{nd['name']} [{nd['group']}]"
                contra_accounts[key]['count'] += 1
                contra_accounts[key]['voucher_types'].add(tag)
                if nd['type'] == '1':
                    contra_accounts[key]['total_debit'] += nd['amt']
                else:
                    contra_accounts[key]['total_credit'] += nd['amt']
            
            # Cross-party check
            if len(debtors_in_voucher) > 1:
                cross_party.append({
                    'tag': tag,
                    'parties': [d['name'] for d in debtors_in_voucher],
                    'amounts': [d['amt'] for d in debtors_in_voucher]
                })

print("=" * 80)
print("1. ALL VOUCHER TYPES IN BUSY DATA")
print("=" * 80)
for tag, info in sorted(voucher_structures.items(), key=lambda x: -x[1]['count']):
    print(f"  {tag:20s} | Total: {info['count']:5d} | Touching Debtors: {info['has_debtor']:5d}")

print("\n" + "=" * 80)
print("2. ALL CONTRA/MASTER ACCOUNTS USED WITH CUSTOMERS")
print("=" * 80)
for name, info in sorted(contra_accounts.items(), key=lambda x: -x[1]['count']):
    vtypes = ', '.join(info['voucher_types'])
    print(f"  {name[:50]:50s} | Used: {info['count']:4d}x | Dr: {info['total_debit']:12.2f} | Cr: {info['total_credit']:12.2f} | In: {vtypes}")

print("\n" + "=" * 80)
print("3. CROSS-PARTY SETTLEMENTS (Multiple debtors in same voucher)")
print("=" * 80)
if cross_party:
    for cp in cross_party:
        print(f"  {cp['tag']:15s} | Parties: {cp['parties']} | Amounts: {cp['amounts']}")
else:
    print("  None found.")

print("\n" + "=" * 80)
print("4. PENDING BILL DETAILS STRUCTURE (from Receipts)")
print("=" * 80)
# Check PendingBillDetails
for f in files:
    tree = ET.parse(f)
    root = tree.getroot()
    for rcpt in root.findall('.//Receipt'):
        pbd = rcpt.find('PendingBillDetails')
        if pbd is not None:
            for bd in pbd:
                print(f"  PendingBillDetail sample: {ET.tostring(bd, encoding='unicode')[:500]}")
            break
    else:
        continue
    break


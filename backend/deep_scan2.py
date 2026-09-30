import xml.etree.ElementTree as ET
from collections import defaultdict

files = ['../BUSY 24-25.DAT', '../BUSY 25-26.DAT', '../BUSY26-27..DAT']

contra_accounts = defaultdict(lambda: {'count': 0, 'total_debit': 0, 'total_credit': 0, 'voucher_types': set()})
cross_party = []
voucher_types = defaultdict(lambda: {'count': 0, 'has_debtor': 0})

for f in files:
    tree = ET.parse(f)
    root = tree.getroot()
    
    # Scan ALL nested vouchers (Sale, Receipt, Journal, SaleReturn, Payment, CrNote, DbNote, etc.)
    for wrapper in root:
        for elem in wrapper:
            tag = elem.tag
            if not isinstance(tag, str):
                continue
            
            acc_entries = elem.find('AccEntries')
            if acc_entries is None:
                continue
            
            voucher_types[tag]['count'] += 1
            
            debtors_in_voucher = []
            non_debtors_in_voucher = []
            
            for acc_det in acc_entries.findall('AccDetail'):
                grp = acc_det.findtext('tmpGroupName') or ''
                name = ' '.join((acc_det.findtext('AccountName') or '').split())
                amt_type = acc_det.findtext('AmountType')
                amt = float(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount') or '0')
                
                if grp == 'Sundry Debtors':
                    debtors_in_voucher.append({'name': name, 'type': amt_type, 'amt': amt})
                else:
                    non_debtors_in_voucher.append({'name': name, 'group': grp, 'type': amt_type, 'amt': amt})
            
            if debtors_in_voucher:
                voucher_types[tag]['has_debtor'] += 1
                
                for nd in non_debtors_in_voucher:
                    key = f"{nd['name']} [{nd['group']}]"
                    contra_accounts[key]['count'] += 1
                    contra_accounts[key]['voucher_types'].add(tag)
                    if nd['type'] == '1':
                        contra_accounts[key]['total_debit'] += nd['amt']
                    else:
                        contra_accounts[key]['total_credit'] += nd['amt']
                
                if len(debtors_in_voucher) > 1:
                    cross_party.append({
                        'tag': tag,
                        'parties': [(d['name'], d['type'], d['amt']) for d in debtors_in_voucher]
                    })

print("=" * 80)
print("1. ACTUAL VOUCHER TYPES (inside wrapper tags)")
print("=" * 80)
for tag, info in sorted(voucher_types.items(), key=lambda x: -x[1]['count']):
    print(f"  {tag:20s} | Total: {info['count']:5d} | Touching Debtors: {info['has_debtor']:5d}")

print("\n" + "=" * 80)
print("2. ALL CONTRA/MASTER ACCOUNTS USED WITH CUSTOMERS (sorted by usage)")
print("=" * 80)
for name, info in sorted(contra_accounts.items(), key=lambda x: -(x[1]['total_debit'] + x[1]['total_credit'])):
    vtypes = ', '.join(info['voucher_types'])
    net = info['total_debit'] - info['total_credit']
    print(f"  {name[:55]:55s} | Used: {info['count']:4d}x | Dr: {info['total_debit']:>14,.2f} | Cr: {info['total_credit']:>14,.2f} | Net: {net:>14,.2f} | In: {vtypes}")

print(f"\n  TOTAL UNIQUE CONTRA ACCOUNTS: {len(contra_accounts)}")

print("\n" + "=" * 80)
print("3. CROSS-PARTY SETTLEMENTS")
print("=" * 80)
if cross_party:
    for cp in cross_party:
        print(f"  {cp['tag']:15s}")
        for p in cp['parties']:
            print(f"    Party: {p[0]:40s} AmtType: {p[1]} Amt: {p[2]:>12,.2f}")
        print()
else:
    print("  None found.")


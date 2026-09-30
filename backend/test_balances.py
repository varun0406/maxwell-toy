import xml.etree.ElementTree as ET
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

def clean(v):
    return ' '.join((v or '').split()) or None

files = ['../BUSY 24-25.DAT', '../BUSY 25-26.DAT', '../BUSY26-27..DAT']

busy_balances = {}
for f in files:
    tree = ET.parse(f)
    root = tree.getroot()
    for acc_det in root.findall('.//AccDetail'):
        grp = acc_det.findtext('tmpGroupName')
        if grp != 'Sundry Debtors':
            continue
        name = clean(acc_det.findtext('AccountName'))
        amt_type = acc_det.findtext('AmountType')
        amt = abs(float(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount') or 0))
        if name not in busy_balances:
            busy_balances[name] = 0
        if amt_type == '1':
            busy_balances[name] += amt
        elif amt_type == '2':
            busy_balances[name] -= amt

session = SessionLocal()
db_balances = {}
rows = session.execute(text("""
    SELECT p.name, 
           COALESCE((SELECT SUM(amount) FROM invoices WHERE party_id = p.id AND is_deleted = false), 0) +
           COALESCE((SELECT SUM(amount) FROM journal_entries WHERE party_id = p.id AND is_deleted = false), 0) -
           COALESCE((SELECT SUM(amount) FROM payments WHERE party_id = p.id AND is_deleted = false), 0) as outstanding
    FROM parties p
""")).fetchall()

for row in rows:
    db_balances[clean(row.name)] = float(row.outstanding)

total_busy = sum(busy_balances.values())
total_db = sum(db_balances.values())

diffs = []
for name in set(list(busy_balances.keys()) + list(db_balances.keys())):
    busy_bal = busy_balances.get(name, 0)
    db_bal = db_balances.get(name, 0)
    diff = busy_bal - db_bal
    if abs(diff) > 1:
        diffs.append({'name': name, 'busy': busy_bal, 'db': db_bal, 'diff': diff})

diffs.sort(key=lambda x: abs(x['diff']), reverse=True)

print(f"Total BUSY Sundry Debtors: {total_busy:>14,.2f}")
print(f"Total DB Outstanding:      {total_db:>14,.2f}")
print(f"Total Difference:          {total_busy - total_db:>14,.2f}")
print()
if diffs:
    print("Per-party differences:")
    for d in diffs:
        print(f"  {d['name'][:35]:35s} | BUSY: {d['busy']:>12,.2f} | DB: {d['db']:>12,.2f} | DIFF: {d['diff']:>12,.2f}")
else:
    print("✅ ALL CUSTOMER BALANCES MATCH PERFECTLY!")

# Also show master accounts
print("\n--- Master Accounts Summary ---")
accts = session.execute(text("""
    SELECT am.name, am.group_name, COUNT(je.id) as cnt, COALESCE(SUM(je.amount), 0) as total
    FROM account_masters am
    LEFT JOIN journal_entries je ON je.account_id = am.id AND je.is_deleted = false
    GROUP BY am.id
    ORDER BY ABS(COALESCE(SUM(je.amount), 0)) DESC
""")).fetchall()
for a in accts:
    print(f"  {a.name:40s} | {(a.group_name or ''):30s} | {a.cnt:4d} entries | Total: {float(a.total):>12,.2f}")

import xml.etree.ElementTree as ET

def clean(v):
    return ' '.join((v or '').split()) or None

files = ['../BUSY 24-25.DAT', '../BUSY 25-26.DAT', '../BUSY26-27..DAT']

busy_balances = {}
for f in files:
    try:
        tree = ET.parse(f)
        root = tree.getroot()
        
        for acc_det in root.findall('.//AccDetail'):
            name = clean(acc_det.findtext('AccountName'))
            amt_type = acc_det.findtext('AmountType')
            amt = abs(float(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount') or 0))
            
            if name not in busy_balances:
                busy_balances[name] = 0
                
            if amt_type == '1': # Debit
                busy_balances[name] += amt
            elif amt_type == '2': # Credit
                busy_balances[name] -= amt
    except Exception as e:
        pass

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text
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

diffs = []
for name, db_bal in db_balances.items():
    if db_bal != 0:
        busy_bal = busy_balances.get(name, 0)
        diff = busy_bal - db_bal
        if abs(diff) > 1:
            diffs.append({'name': name, 'busy': busy_bal, 'db': db_bal, 'diff': diff})

diffs.sort(key=lambda x: abs(x['diff']), reverse=True)
print("DB Accounts differing from entire BUSY AccDetail Ledger:")
for d in diffs:
    print(f"{d['name'][:25]:25} | BUSY: {d['busy']:12.2f} | DB: {d['db']:12.2f} | DIFF: {d['diff']:12.2f}")

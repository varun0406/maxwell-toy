import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text
import xml.etree.ElementTree as ET

session = SessionLocal()
res = session.execute(text("""
    SELECT amount, payment_date FROM payments WHERE party_id = (SELECT id FROM parties WHERE name = 'RAJA BHAI(SURAT)') AND is_deleted = false
""")).fetchall()

db_credits = []
for r in res:
    db_credits.append(('PAYMENT', float(r.amount), r.payment_date))

res2 = session.execute(text("""
    SELECT amount, entry_date, description FROM journal_entries WHERE party_id = (SELECT id FROM parties WHERE name = 'RAJA BHAI(SURAT)') AND is_deleted = false
""")).fetchall()
for r in res2:
    db_credits.append(('JOURNAL', float(r.amount), r.entry_date))

db_credits.sort(key=lambda x: abs(x[1]))

busy_credits = []
party_name = 'RAJA BHAI(SURAT)'
files = ['../BUSY 24-25.DAT', '../BUSY 25-26.DAT', '../BUSY26-27..DAT']
for f in files:
    tree = ET.parse(f)
    root = tree.getroot()
    for acc_det in root.findall('.//AccDetail'):
        name = ' '.join((acc_det.findtext('AccountName') or '').split())
        if name != party_name:
            continue
            
        amt_type = acc_det.findtext('AmountType')
        amt = abs(float(acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount') or 0))
        
        if amt_type == '2': # Credit
            vouch = acc_det.find('../../..')
            vch_type = vouch.findtext('VchType') if vouch else 'Unknown'
            busy_credits.append((vch_type, amt))

busy_credits.sort(key=lambda x: x[1])

print("DB Credits that might not be in BUSY:")
for d in db_credits:
    amt = abs(d[1])
    found = False
    for i, b in enumerate(busy_credits):
        if abs(b[1] - amt) < 1:
            found = True
            busy_credits.pop(i)
            break
    if not found:
        print(f"DB Only: {d}")

print("BUSY Credits that might not be in DB:")
for b in busy_credits:
    print(f"BUSY Only: {b}")

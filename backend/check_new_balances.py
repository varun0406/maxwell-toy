import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models import Party, Invoice, Payment, JournalEntry
from sqlalchemy import func

session = SessionLocal()
parties = session.query(Party).all()

total_calculated = 0
total_busy = 0
differences = []

for p in parties:
    invs = session.query(func.sum(Invoice.amount)).filter(Invoice.party_id == p.id, Invoice.is_deleted == False).scalar() or 0
    pays = session.query(func.sum(Payment.amount)).filter(Payment.party_id == p.id, Payment.is_deleted == False).scalar() or 0
    jrns = session.query(func.sum(JournalEntry.amount)).filter(JournalEntry.party_id == p.id, JournalEntry.is_deleted == False).scalar() or 0
    
    calc_bal = float(invs) + float(jrns) - float(pays)
    busy_bal = float(p.busy_closing_balance or 0)
    
    total_calculated += calc_bal
    total_busy += busy_bal
    
    if abs(calc_bal - busy_bal) > 0.01:
        differences.append((p.name, calc_bal, busy_bal, calc_bal - busy_bal))

print(f"Total DB Calculated: {total_calculated:,.2f}")
print(f"Total BUSY Master:   {total_busy:,.2f}")
print(f"Total Difference:    {total_calculated - total_busy:,.2f}")
if differences:
    print("\nParties with differences:")
    for d in differences:
        print(f"{d[0]}: Calc={d[1]}, BUSY={d[2]}, Diff={d[3]}")
else:
    print("\n✅ NO DIFFERENCES!")

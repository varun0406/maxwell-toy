from app.database import SessionLocal
from app.models import Party, Invoice, Payment, JournalEntry, PaymentAllocation
from sqlalchemy import func

session = SessionLocal()
parties = session.query(Party).all()

differences = []

for p in parties:
    invs = session.query(func.sum(Invoice.amount)).filter(Invoice.party_id == p.id, Invoice.is_deleted == False).scalar() or 0
    pays = session.query(func.sum(Payment.amount)).filter(Payment.party_id == p.id, Payment.is_deleted == False).scalar() or 0
    jrns = session.query(func.sum(JournalEntry.amount)).filter(JournalEntry.party_id == p.id, JournalEntry.is_deleted == False).scalar() or 0
    
    calc_bal = float(invs) + float(jrns) - float(pays)
    busy_bal = float(p.busy_closing_balance or 0)
    
    unpaid_bills = float(session.query(func.sum(Invoice.balance_due)).filter(Invoice.party_id == p.id, Invoice.is_deleted == False).scalar() or 0)
    
    db_diff = calc_bal - busy_bal
    bills_diff = unpaid_bills - calc_bal
    
    if abs(db_diff) > 0.01 or abs(bills_diff) > 0.01:
        differences.append((p.name, busy_bal, calc_bal, unpaid_bills, db_diff, bills_diff))

differences.sort(key=lambda x: abs(x[4]), reverse=True)

with open('final_differences.md', 'w') as f:
    f.write("# Final Party Discrepancies\n\n")
    f.write("| Party Name | BUSY Master Balance | DB Calc Balance | DB Diff | Unpaid Bills Sum | Unallocated Payments (Bills Diff) |\n")
    f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
    for name, busy, calc, unpaid, db_diff, bills_diff in differences:
        f.write(f"| {name} | {busy:,.2f} | {calc:,.2f} | **{db_diff:,.2f}** | {unpaid:,.2f} | {bills_diff:,.2f} |\n")

print(f"Generated report for {len(differences)} parties with differences.")

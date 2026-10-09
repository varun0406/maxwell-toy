import os
import sys
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import engine

accounts = [
    # ASSETS
    {"code": "CASH", "name": "Cash on Hand", "type": "ASSET", "party": False, "sys": True},
    {"code": "BANK", "name": "Bank Account", "type": "ASSET", "party": False, "sys": True},
    {"code": "DEBTORS", "name": "Sundry Debtors", "type": "ASSET", "party": True, "sys": True},
    # LIABILITIES
    {"code": "CREDITORS", "name": "Sundry Creditors", "type": "LIABILITY", "party": True, "sys": True},
    {"code": "GST_PAYABLE", "name": "GST Payable", "type": "LIABILITY", "party": False, "sys": True},
    # EQUITY
    {"code": "CAPITAL", "name": "Capital Account", "type": "EQUITY", "party": False, "sys": True},
    {"code": "RETAINED", "name": "Retained Earnings", "type": "EQUITY", "party": False, "sys": True},
    # INCOME
    {"code": "SALES", "name": "Sales Account", "type": "INCOME", "party": False, "sys": True},
    {"code": "DISC_REC", "name": "Discount Received", "type": "INCOME", "party": False, "sys": True},
    # EXPENSES
    {"code": "PURCHASES", "name": "Purchases Account", "type": "EXPENSE", "party": False, "sys": True},
    {"code": "SALES_RET", "name": "Sales Return", "type": "EXPENSE", "party": False, "sys": True},
    {"code": "DISC_ALLOW", "name": "Discount Allowed", "type": "EXPENSE", "party": False, "sys": True},
    {"code": "BANK_CHG", "name": "Bank Charges", "type": "EXPENSE", "party": False, "sys": True},
]

with engine.connect() as conn:
    for acc in accounts:
        # Check if exists
        exists = conn.execute(text("SELECT id FROM accounts WHERE code = :code"), {"code": acc["code"]}).fetchone()
        if not exists:
            conn.execute(
                text("""
                    INSERT INTO accounts (code, name, account_type, is_party_control, is_system, active)
                    VALUES (:code, :name, :type, :party, :sys, true)
                """),
                {"code": acc["code"], "name": acc["name"], "type": acc["type"], "party": acc["party"], "sys": acc["sys"]}
            )
            print(f"Created account: {acc['name']}")
        else:
            print(f"Account {acc['name']} already exists.")
    
    conn.commit()
    print("Seed complete.")

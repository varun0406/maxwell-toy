import os
import sys
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import engine

base_accounts = [
    # Core automatic accounts
    {"code": "DEBTORS", "name": "Sundry Debtors", "type": "ASSET", "party": True, "sys": True},
    {"code": "CREDITORS", "name": "Sundry Creditors", "type": "LIABILITY", "party": True, "sys": True},
    {"code": "SALES", "name": "Sales Account", "type": "INCOME", "party": False, "sys": True},
    {"code": "SALES_RET", "name": "Sales Return", "type": "EXPENSE", "party": False, "sys": True},
    {"code": "PURCHASES", "name": "Purchases Account", "type": "EXPENSE", "party": False, "sys": True},
    {"code": "DISC_ALLOW", "name": "Discount Allowed", "type": "EXPENSE", "party": False, "sys": True},
]

with engine.connect() as conn:
    # 1. Discover payment modes dynamically from existing transactions
    modes_result = conn.execute(text("SELECT DISTINCT COALESCE(mode, 'CASH') as p_mode FROM payments WHERE COALESCE(is_deleted, false) = false")).fetchall()
    
    seen_modes = set()
    for row in modes_result:
        mode = row.p_mode.strip().upper()
        if mode and mode not in seen_modes:
            seen_modes.add(mode)
            base_accounts.append({
                "code": mode,
                "name": "Cash on Hand" if mode == "CASH" else f"{mode.capitalize()} Account",
                "type": "ASSET",
                "party": False,
                "sys": True
            })

    # 2. Insert all base and discovered accounts
    for acc in base_accounts:
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
    print("Automatic account generation from transactions complete.")

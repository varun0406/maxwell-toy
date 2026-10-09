import os
import sys
from datetime import datetime, timezone
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal, engine
from app import models

def sync_historical():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Ensure default accounts exist
        base_accounts = [
            {"code": "DEBTORS", "name": "Sundry Debtors", "type": "ASSET", "party": True, "sys": True},
            {"code": "SALES", "name": "Sales Account", "type": "INCOME", "party": False, "sys": True},
            {"code": "CASH", "name": "Cash on Hand", "type": "ASSET", "party": False, "sys": True},
            {"code": "BANK", "name": "Bank Account", "type": "ASSET", "party": False, "sys": True},
            {"code": "UPI", "name": "UPI Account", "type": "ASSET", "party": False, "sys": True},
            {"code": "CHEQUE", "name": "Cheque Account", "type": "ASSET", "party": False, "sys": True},
        ]
        
        for acc in base_accounts:
            existing = db.query(models.Account).filter(models.Account.code == acc["code"]).first()
            if not existing:
                a = models.Account(
                    code=acc["code"],
                    name=acc["name"],
                    account_type=acc["type"],
                    is_party_control=acc["party"],
                    is_system=acc["sys"],
                    active=True
                )
                db.add(a)
        db.commit()

        # Get accounts
        acc_map = {a.code: a.id for a in db.query(models.Account).all()}
        
        # 1. Sync Invoices (SALE)
        invoices = db.query(models.Invoice).filter(models.Invoice.is_deleted == False).all()
        for inv in invoices:
            # Check if voucher exists
            exists = db.query(models.Voucher).filter(models.Voucher.source == "INVOICE", models.Voucher.source_ref == str(inv.id)).first()
            if exists:
                continue
            
            print(f"Syncing Invoice {inv.invoice_number}")
            v = models.Voucher(
                voucher_type="SALE",
                voucher_date=inv.invoice_date,
                narration=f"Sales Invoice #{inv.invoice_number}",
                status="POSTED",
                created_by=inv.created_by,
                posted_at=inv.created_at,
                source="INVOICE",
                source_ref=str(inv.id)
            )
            db.add(v)
            db.flush()
            
            # Debit Debtors (with party_id)
            db.add(models.VoucherLine(
                voucher_id=v.id,
                account_id=acc_map["DEBTORS"],
                party_id=inv.party_id,
                debit=inv.amount,
                credit=0
            ))
            # Credit Sales
            db.add(models.VoucherLine(
                voucher_id=v.id,
                account_id=acc_map["SALES"],
                debit=0,
                credit=inv.amount
            ))

        # 2. Sync Payments (RECEIPT)
        payments = db.query(models.Payment).filter(models.Payment.is_deleted == False).all()
        for pmt in payments:
            exists = db.query(models.Voucher).filter(models.Voucher.source == "PAYMENT", models.Voucher.source_ref == str(pmt.id)).first()
            if exists:
                continue
                
            print(f"Syncing Payment #{pmt.id}")
            v = models.Voucher(
                voucher_type="RECEIPT",
                voucher_date=pmt.payment_date,
                narration=f"Receipt via {pmt.mode} - {pmt.note or ''}".strip(),
                status="POSTED",
                created_by=pmt.created_by,
                posted_at=pmt.created_at,
                source="PAYMENT",
                source_ref=str(pmt.id)
            )
            db.add(v)
            db.flush()
            
            # Debit Cash/Bank/UPI based on mode
            mode_code = (pmt.mode or "CASH").upper()
            acc_id = acc_map.get(mode_code, acc_map["CASH"])
            
            db.add(models.VoucherLine(
                voucher_id=v.id,
                account_id=acc_id,
                debit=pmt.amount,
                credit=0
            ))
            # Credit Debtors (with party_id)
            db.add(models.VoucherLine(
                voucher_id=v.id,
                account_id=acc_map["DEBTORS"],
                party_id=pmt.party_id,
                debit=0,
                credit=pmt.amount
            ))

        db.commit()
        print("Sync complete!")

    finally:
        db.close()

if __name__ == "__main__":
    sync_historical()

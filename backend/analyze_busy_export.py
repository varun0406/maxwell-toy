"""Inspect BUSY XML exports without touching the database.

Examples:
  python analyze_busy_export.py ../BUSY.DAT ../BUSY26-27..DAT --out busy-map.json
  python analyze_busy_export.py ../BUSY.DAT --samples 5
"""

import argparse
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


def text(node, name):
    return (node.findtext(name) or "").strip()


def analyze_master(root, samples):
    accounts = root.findall(".//Account")
    groups = Counter(text(account, "ParentGroup") for account in accounts)
    debtor_accounts = [a for a in accounts if text(a, "ParentGroup") == "Sundry Debtors"]
    supplier_accounts = [a for a in accounts if text(a, "ParentGroup") == "Sundry Creditors"]

    def account_sample(account):
        address = account.find("Address")
        return {
            "name": text(account, "Name"),
            "parent_group": text(account, "ParentGroup"),
            "opening_balance": text(account, "OPBal"),
            "broker": text(account, "BrokerName") or text(account, "tmpBrokerName"),
            "phone": text(address, "Mobile") if address is not None else "",
            "whatsapp": text(address, "WhatsAppNo") if address is not None else "",
            "gstin": text(address, "GSTNo") if address is not None else "",
            "address": {
                "line1": text(address, "Address1") if address is not None else "",
                "line2": text(address, "Address2") if address is not None else "",
                "line3": text(address, "Address3") if address is not None else "",
                "line4": text(address, "Address4") if address is not None else "",
                "city": text(address, "CityName") if address is not None else "",
                "state": text(address, "StateName") if address is not None else "",
            },
        }

    return {
        "record_type": "master",
        "accounts": len(accounts),
        "account_groups": dict(groups),
        "sundry_debtors": len(debtor_accounts),
        "sundry_creditors": len(supplier_accounts),
        "debtors_missing_address": sum(a.find("Address") is None for a in debtor_accounts),
        "suppliers_missing_address": sum(a.find("Address") is None for a in supplier_accounts),
        "samples": {
            "debtors": [account_sample(a) for a in debtor_accounts[:samples]],
            "suppliers": [account_sample(a) for a in supplier_accounts[:samples]],
        },
    }


def analyze_transactions(root, samples):
    selectors = {
        "sales": ".//Sales/Sale",
        "sale_returns": ".//SlRts/SaleReturn",
        "receipts": ".//Rcpts/Receipt",
        "journals": ".//Jrnls/Journal",
        "credit_notes": ".//CrNts/CrNt",
    }
    result = {name: len(root.findall(selector)) for name, selector in selectors.items()}
    vouchers = []
    parties = Counter()
    for name, selector in selectors.items():
        rows = root.findall(selector)
        for row in rows:
            voucher = text(row, "VchNo")
            if voucher:
                vouchers.append((name, voucher))
            party = text(row, "MasterName1")
            if party:
                parties[party] += 1

    duplicate_vouchers = [
        {"voucher": voucher, "count": count}
        for (voucher, count) in Counter(voucher for _, voucher in vouchers).items()
        if count > 1
    ]
    result.update({
        "unique_parties_referenced": len(parties),
        "top_parties": [{"name": name, "transactions": count} for name, count in parties.most_common(samples)],
        "duplicate_vouchers_across_types": duplicate_vouchers[:samples * 5],
        "missing_party_name": sum(not text(row, "MasterName1") for selector in selectors.values() for row in root.findall(selector)),
    })
    return result


def analyze(path, samples):
    root = ET.parse(path).getroot()
    counts = Counter(element.tag for element in root.iter())
    report = {
        "file": str(path),
        "fin_year": root.attrib.get("FinYear"),
        "xml_element_count": sum(counts.values()),
        "top_xml_tags": dict(counts.most_common(40)),
    }
    has_transactions = any(root.findall(selector) for selector in (
        ".//Sales/Sale", ".//SlRts/SaleReturn", ".//Rcpts/Receipt",
        ".//Jrnls/Journal", ".//CrNts/CrNt",
    ))
    if has_transactions:
        report.update({"record_type": "transactions", **analyze_transactions(root, samples)})
    else:
        report.update(analyze_master(root, samples))
    return report


def main():
    parser = argparse.ArgumentParser(description="Create a read-only BUSY export mapping report.")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, help="Write JSON report to this path.")
    parser.add_argument("--samples", type=int, default=5, help="Number of sample records per category.")
    args = parser.parse_args()
    report = {"files": [analyze(path, max(1, args.samples)) for path in args.files]}
    encoded = json.dumps(report, indent=2, ensure_ascii=False)
    print(encoded)
    if args.out:
        args.out.write_text(encoded + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
